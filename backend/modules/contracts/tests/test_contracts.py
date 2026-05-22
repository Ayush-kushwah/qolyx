import pytest
import uuid
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from backend.core.database import Base
from backend.modules.contracts.models import Contract, ContractViolation
from backend.modules.contracts.services import (
    validate_pipeline_run,
    generate_contract_from_table,
    initialize_contracts,
    get_violations_for_run,
    get_total_penalty_for_run
)
from backend.modules.contracts.schemas import ColumnExpectation, GenerateContractResponse
from backend.modules.ingestion.models import BronzeFinancialCandle, BronzeFdaEvent, BronzeGithubEvent


@pytest.fixture(scope="function")
def db_session():
    """Fixture to create an in-memory SQLite database, run migrations (create tables), and yield a session."""
    engine = create_engine("sqlite:///:memory:")
    # Ensure models are imported so they are registered on Base.metadata
    Base.metadata.create_all(bind=engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def mock_publish():
    """Fixture to auto-mock the publish function to avoid Redis dependencies during tests."""
    with patch("backend.modules.contracts.services.publish") as mock:
        yield mock


def get_candles_contract_schema():
    """Returns a valid expectation schema for bronze_financial_candles.
    
    Since SQLite compiles PostgreSQL UUID columns to NUMERIC, we expect 'float' for id and pipeline_run_id.
    """
    return {
        "id": {"data_type": "float", "nullable": False, "is_required": True},
        "pipeline_run_id": {"data_type": "float", "nullable": False, "is_required": True},
        "symbol": {"data_type": "string", "nullable": False, "is_required": True},
        "open_price": {"data_type": "float", "nullable": True, "is_required": False},
        "high_price": {"data_type": "float", "nullable": True, "is_required": False},
        "low_price": {"data_type": "float", "nullable": True, "is_required": False},
        "close_price": {"data_type": "float", "nullable": True, "is_required": False},
        "volume": {"data_type": "integer", "nullable": True, "is_required": False},
        "candle_timestamp": {"data_type": "datetime", "nullable": False, "is_required": True},
        "ingested_at": {"data_type": "datetime", "nullable": False, "is_required": True}
    }


def test_contract_creation(db_session):
    """Test creating a Contract object and retrieving it."""
    contract = Contract(
        name="test_candle_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition={
            "symbol": {"data_type": "string", "nullable": False, "is_required": True},
            "close_price": {"data_type": "float", "nullable": True, "is_required": False}
        },
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)

    assert contract.id is not None
    retrieved = db_session.query(Contract).filter_by(id=contract.id).first()
    assert retrieved is not None
    assert retrieved.name == "test_candle_contract"
    assert retrieved.schema_definition["symbol"]["data_type"] == "string"


def test_contract_validation_passes_no_contract(db_session):
    """Test validation when no active contract exists for the table."""
    pipeline_run_id = uuid.uuid4()
    result = validate_pipeline_run(db_session, "bronze_financial_candles", pipeline_run_id)
    assert result.is_valid is True
    assert result.violation_count == 0
    assert result.total_penalty == 0
    assert len(result.violations) == 0


def test_contract_validation_passes_with_valid_schema(db_session):
    """Test validation passes when table matches contract schema and there are no violations."""
    contract = Contract(
        name="candles_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition=get_candles_contract_schema(),
        is_active=True
    )
    db_session.add(contract)

    # Add a valid row matching this pipeline_run_id
    pipeline_run_id = uuid.uuid4()
    candle = BronzeFinancialCandle(
        id=uuid.uuid4(),
        pipeline_run_id=pipeline_run_id,
        symbol="AAPL",
        open_price=150.0,
        high_price=155.0,
        low_price=149.0,
        close_price=152.0,
        volume=100,
        candle_timestamp=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc)
    )
    db_session.add(candle)
    db_session.commit()

    result = validate_pipeline_run(db_session, "bronze_financial_candles", pipeline_run_id)
    assert result.is_valid is True
    assert result.violation_count == 0
    assert result.total_penalty == 0


def test_contract_validation_fails_missing_column(db_session):
    """Test validation fails when a required column in the contract is not in the database table."""
    schema = get_candles_contract_schema()
    schema["non_existent_column"] = {"data_type": "string", "nullable": False, "is_required": True}

    contract = Contract(
        name="candles_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition=schema,
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()

    pipeline_run_id = uuid.uuid4()
    result = validate_pipeline_run(db_session, "bronze_financial_candles", pipeline_run_id)
    assert result.is_valid is False
    assert result.violation_count == 1
    assert result.violations[0].violation_type == "missing_column"
    assert result.violations[0].column_name == "non_existent_column"


def test_contract_validation_fails_multiple_missing_columns(db_session):
    """Test validation fails with multiple missing columns, verifying total penalty caps at 40."""
    schema = get_candles_contract_schema()
    for i in range(5):
        schema[f"non_existent_{i}"] = {"data_type": "string", "nullable": False, "is_required": True}

    contract = Contract(
        name="candles_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition=schema,
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()

    pipeline_run_id = uuid.uuid4()
    result = validate_pipeline_run(db_session, "bronze_financial_candles", pipeline_run_id)
    assert result.is_valid is False
    assert result.violation_count == 5
    assert result.total_penalty == 40  # Capped at 40


def test_contract_validation_fails_wrong_type(db_session):
    """Test validation fails when a column in the database has a different type than expected."""
    schema = get_candles_contract_schema()
    schema["volume"] = {"data_type": "string", "nullable": True, "is_required": False}  # DB has type integer

    contract = Contract(
        name="candles_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition=schema,
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()

    pipeline_run_id = uuid.uuid4()
    result = validate_pipeline_run(db_session, "bronze_financial_candles", pipeline_run_id)
    assert result.is_valid is False
    assert result.violation_count == 1
    assert result.violations[0].violation_type == "wrong_type"
    assert result.violations[0].column_name == "volume"
    assert result.violations[0].expected_value == "string"


def test_violations_stored_in_database(db_session):
    """Test that validation violations are stored correctly in the database."""
    schema = get_candles_contract_schema()
    schema["non_existent_column"] = {"data_type": "string", "nullable": False, "is_required": True}

    contract = Contract(
        name="candles_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition=schema,
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()

    pipeline_run_id = uuid.uuid4()
    validate_pipeline_run(db_session, "bronze_financial_candles", pipeline_run_id)

    db_violations = db_session.query(ContractViolation).filter_by(pipeline_run_id=pipeline_run_id).all()
    assert len(db_violations) == 1
    assert db_violations[0].violation_type == "missing_column"
    assert db_violations[0].column_name == "non_existent_column"
    assert db_violations[0].penalty_amount == 10


def test_total_penalty_calculation(db_session):
    """Test get_total_penalty_for_run calculates properly and caps at 40."""
    contract = Contract(
        name="candles_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition={},
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()

    pipeline_run_id = uuid.uuid4()

    # 0 violations
    assert get_total_penalty_for_run(db_session, pipeline_run_id) == 0

    # Add violations
    for i in range(5):
        viol = ContractViolation(
            contract_id=contract.id,
            pipeline_run_id=pipeline_run_id,
            violation_type="missing_column",
            column_name=f"col_{i}",
            penalty_amount=10,
            description="Missing column test"
        )
        db_session.add(viol)
    db_session.commit()

    # 5 violations -> 50 points, capped at 40
    penalty = get_total_penalty_for_run(db_session, pipeline_run_id)
    assert penalty == 40


def test_initialize_contracts_seeds_all_three(db_session):
    """Test that initialize_contracts seeds all three default contracts."""
    contracts = initialize_contracts(db_session)
    assert len(contracts) == 3

    names = {c.name for c in contracts}
    expected_names = {
        "Finnhub Financial Candles Contract",
        "FDA Adverse Events Contract",
        "GitHub Archive Events Contract"
    }
    assert names == expected_names

    # Run again, shouldn't duplicate
    contracts_second_run = initialize_contracts(db_session)
    assert len(contracts_second_run) == 3
    all_db_contracts = db_session.query(Contract).all()
    assert len(all_db_contracts) == 3


def test_generate_contract_from_table(db_session):
    """Test that generate_contract_from_table creates a correct proposal from an existing table's schema."""
    response = generate_contract_from_table(db_session, "bronze_financial_candles", "generated_candles")
    assert isinstance(response, GenerateContractResponse)
    assert response.table_name == "bronze_financial_candles"
    assert response.name == "generated_candles"

    schema = response.schema_definition
    assert "symbol" in schema
    assert schema["symbol"].data_type == "string"
    assert schema["symbol"].nullable is False
    assert schema["symbol"].is_required is True

    assert "volume" in schema
    assert schema["volume"].data_type == "integer"
    assert schema["volume"].nullable is True
    assert schema["volume"].is_required is False


def test_generate_contract_saves_after_edit(db_session):
    """Test that a generated contract proposal can be saved to the database after modification."""
    # Generate proposal
    proposal = generate_contract_from_table(db_session, "bronze_financial_candles", "edited_candles_contract")
    
    # Modify proposal definition using model_copy on the frozen objects
    new_symbol = proposal.schema_definition["symbol"].model_copy(update={"max_length": 20})
    new_open_price = proposal.schema_definition["open_price"].model_copy(update={"is_required": True})

    new_schema_def = dict(proposal.schema_definition)
    new_schema_def["symbol"] = new_symbol
    new_schema_def["open_price"] = new_open_price

    # Save to database
    schema_dict = {
        col_name: {
            "data_type": expectation.data_type,
            "nullable": expectation.nullable,
            "max_length": expectation.max_length,
            "is_required": expectation.is_required
        }
        for col_name, expectation in new_schema_def.items()
    }
    contract = Contract(
        name=proposal.name,
        table_name=proposal.table_name,
        version=1,
        schema_definition=schema_dict,
        is_active=True
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)

    # Retrieve and assert
    retrieved = db_session.query(Contract).filter_by(name="edited_candles_contract").first()
    assert retrieved is not None
    assert retrieved.schema_definition["symbol"]["max_length"] == 20
    assert retrieved.schema_definition["open_price"]["is_required"] is True
