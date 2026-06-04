import pytest
import uuid
import logging
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.modules.trust_score.models import TrustScore
from backend.modules.contracts.models import Contract, ContractViolation
from backend.modules.anomaly.models import AnomalyDetection
from backend.modules.trust_score.service import TrustScoreService

logger = logging.getLogger("qolyx.trust_score.test")


@pytest.fixture(scope="function")
def db_session():
    """Fixture to create an in-memory SQLite database, run migrations, and yield a session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Define a helper to attach SQLite schemas conditionally
    def attach_schema_if_needed(conn, name):
        res = conn.execute(text("PRAGMA database_list")).fetchall()
        attached = {row[1] for row in res}
        if name not in attached:
            conn.execute(text(f"ATTACH DATABASE ':memory:' AS {name}"))
            conn.commit()

    # Attach schemas in SQLite for testing
    with engine.connect() as conn:
        attach_schema_if_needed(conn, "public_silver")
        attach_schema_if_needed(conn, "test_results")
        conn.execute(text("DROP TABLE IF EXISTS test_results.dbt_test_results"))
        conn.execute(text("""
            CREATE TABLE test_results.dbt_test_results (
                id VARCHAR(36) PRIMARY KEY,
                status VARCHAR(50),
                execution_completed_at TIMESTAMP
            )
        """))
        conn.commit()

    # Ensure models are registered on Base.metadata
    from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()

    # Also attach schemas for the session connection if not already attached
    attach_schema_if_needed(session, "public_silver")
    attach_schema_if_needed(session, "test_results")

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def mock_publish():
    """Fixture to auto-mock the publish_with_retry function to avoid Redis dependencies."""
    with patch("backend.modules.trust_score.service.publish_with_retry") as mock:
        yield mock


# Test 1: _validate_and_cap_penalties within bounds
def test_validate_and_cap_penalties_within_bounds():
    """Test that penalties below the maximum caps are unchanged."""
    penalties = {
        "contract_penalty": 20,
        "anomaly_penalty": 10,
        "freshness_penalty": 15,
        "volume_penalty": 10,
        "dbt_penalty": 5
    }
    capped = TrustScoreService._validate_and_cap_penalties(penalties)
    assert capped == penalties


# Test 2: _validate_and_cap_penalties exceeding caps
def test_validate_and_cap_penalties_exceeding_caps():
    """Test that individual penalties are correctly capped to their respective maximum values."""
    penalties = {
        "contract_penalty": 50,  # Cap is 40
        "anomaly_penalty": 30,   # Cap is 20
        "freshness_penalty": 40, # Cap is 30
        "volume_penalty": 35,    # Cap is 30
        "dbt_penalty": 25        # Cap is 20
    }
    capped = TrustScoreService._validate_and_cap_penalties(penalties)
    assert capped["contract_penalty"] == 40
    assert capped["anomaly_penalty"] == 20
    assert capped["freshness_penalty"] == 30
    assert capped["volume_penalty"] == 30
    assert capped["dbt_penalty"] == 20


# Test 3: Status mapping - HEALTHY
def test_status_mapping_healthy():
    """Test status mapping for score >= 80 (HEALTHY)."""
    assert TrustScoreService._get_status_from_score(100) == "HEALTHY"
    assert TrustScoreService._get_status_from_score(80) == "HEALTHY"


# Test 4: Status mapping - WARNING
def test_status_mapping_warning():
    """Test status mapping for score 60 to 79 (WARNING)."""
    assert TrustScoreService._get_status_from_score(79) == "WARNING"
    assert TrustScoreService._get_status_from_score(60) == "WARNING"


# Test 5: Status mapping - DEGRADED
def test_status_mapping_degraded():
    """Test status mapping for score 40 to 59 (DEGRADED)."""
    assert TrustScoreService._get_status_from_score(59) == "DEGRADED"
    assert TrustScoreService._get_status_from_score(40) == "DEGRADED"


# Test 6: Status mapping - CRITICAL
def test_status_mapping_critical():
    """Test status mapping for score < 40 (CRITICAL)."""
    assert TrustScoreService._get_status_from_score(39) == "CRITICAL"
    assert TrustScoreService._get_status_from_score(0) == "CRITICAL"


# Test 7: _validate_penalties_structure validations
def test_validate_penalties_structure_invalid():
    """Test that invalid types, missing keys, and negative values raise ValueError."""
    # 1. Invalid type (not a dict)
    with pytest.raises(ValueError, match="Penalties must be a dictionary"):
        TrustScoreService._validate_penalties_structure([("contract_penalty", 10)])  # type: ignore

    # 2. Missing keys
    incomplete_penalties = {
        "contract_penalty": 10,
        "anomaly_penalty": 10,
        "freshness_penalty": 10
        # Missing volume_penalty and dbt_penalty
    }
    with pytest.raises(ValueError, match="Missing required penalty keys"):
        TrustScoreService._validate_penalties_structure(incomplete_penalties)

    # 3. Negative values
    negative_penalties = {
        "contract_penalty": -10,
        "anomaly_penalty": 10,
        "freshness_penalty": 10,
        "volume_penalty": 10,
        "dbt_penalty": 10
    }
    with pytest.raises(ValueError, match="must be a non-negative integer"):
        TrustScoreService._validate_penalties_structure(negative_penalties)

    # 4. Non-integer values
    float_penalties = {
        "contract_penalty": 10.5,  # type: ignore
        "anomaly_penalty": 10,
        "freshness_penalty": 10,
        "volume_penalty": 10,
        "dbt_penalty": 10
    }
    with pytest.raises(ValueError, match="must be a non-negative integer"):
        TrustScoreService._validate_penalties_structure(float_penalties)


# Test 8: calculate_penalties on empty database
def test_calculate_penalties_empty_run(db_session):
    """Test calculate_penalties returns zero penalties when no violations or anomalies exist."""
    run_id = uuid.uuid4()
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties == {
        "contract_penalty": 0,
        "anomaly_penalty": 0,
        "dbt_penalty": 0,
        "freshness_penalty": 0,
        "volume_penalty": 0
    }


# Test 9: calculate_penalties with contract violations
def test_calculate_penalties_contract_violations(db_session):
    """Test calculate_penalties sums contract violations and caps at 40."""
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # Seed contract first (non-nullable relation for ContractViolation)
    contract = Contract(
        id=uuid.uuid4(),
        name="test_candle_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition={},
        is_active=True,
        created_at=now,
        updated_at=now
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)
    
    # Add violations
    viol1 = ContractViolation(
        id=uuid.uuid4(),
        contract_id=contract.id,
        pipeline_run_id=run_id,
        column_name="close_price",
        violation_type="null_value",
        penalty_amount=10,
        description="Null value in close_price",
        created_at=now
    )
    viol2 = ContractViolation(
        id=uuid.uuid4(),
        contract_id=contract.id,
        pipeline_run_id=run_id,
        column_name="volume",
        violation_type="wrong_type",
        penalty_amount=10,
        description="Volume should be integer",
        created_at=now
    )
    db_session.add(viol1)
    db_session.add(viol2)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["contract_penalty"] == 20
    
    # Add more violations to exceed cap
    for i in range(3):
        viol = ContractViolation(
            id=uuid.uuid4(),
            contract_id=contract.id,
            pipeline_run_id=run_id,
            column_name=f"col_{i}",
            violation_type="wrong_type",
            penalty_amount=10,
            description="Exceed cap violations",
            created_at=now
        )
        db_session.add(viol)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["contract_penalty"] == 40  # Capped at 40


# Test 10: calculate_penalties with anomaly detections
def test_calculate_penalties_anomaly_detections(db_session):
    """Test calculate_penalties sums anomaly penalties (excluding false positives) and caps at 20."""
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    # 1. Add valid anomaly
    anom1 = AnomalyDetection(
        id=uuid.uuid4(),
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        anomaly_type="volume_drop",
        anomaly_score=0.75,
        anomaly_penalty=15,
        is_false_positive=False,
        explanation="Row count deviated",
        created_at=now,
        updated_at=now
    )
    # 2. Add anomaly marked as false positive (should be excluded)
    anom_fp = AnomalyDetection(
        id=uuid.uuid4(),
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        anomaly_type="volume_spike",
        anomaly_score=0.9,
        anomaly_penalty=18,
        is_false_positive=True,
        explanation="Row count spike ignored",
        created_at=now,
        updated_at=now
    )
    db_session.add(anom1)
    db_session.add(anom_fp)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["anomaly_penalty"] == 15
    
    # 3. Add more anomalies to exceed cap
    anom2 = AnomalyDetection(
        id=uuid.uuid4(),
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        anomaly_type="freshness_delay",
        anomaly_score=0.5,
        anomaly_penalty=10,
        is_false_positive=False,
        explanation="Freshness delay",
        created_at=now,
        updated_at=now
    )
    db_session.add(anom2)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["anomaly_penalty"] == 20  # 15 + 10 = 25, capped at 20


# Test 11: calculate_trust_score core logic
def test_calculate_trust_score():
    """Test calculate_trust_score calculates score, total penalties, and correct status."""
    penalties = {
        "contract_penalty": 20,
        "anomaly_penalty": 10,
        "freshness_penalty": 0,
        "volume_penalty": 0,
        "dbt_penalty": 0
    }
    score, total, status = TrustScoreService.calculate_trust_score(penalties)
    assert score == 70
    assert total == 30
    assert status == "WARNING"
    
    # Test max penalties clamping score to 0
    max_penalties = {
        "contract_penalty": 40,
        "anomaly_penalty": 20,
        "freshness_penalty": 30,
        "volume_penalty": 30,
        "dbt_penalty": 20
    }
    score, total, status = TrustScoreService.calculate_trust_score(max_penalties)
    assert score == 0
    assert total == 100
    assert status == "CRITICAL"


# Test 12: save_trust_score creates and updates (idempotency + event publishing)
def test_save_trust_score_creates_and_updates(db_session, mock_publish):
    """Test save_trust_score idempotently creates/updates and emits event."""
    run_id = uuid.uuid4()
    penalties = {
        "contract_penalty": 10,
        "anomaly_penalty": 5,
        "freshness_penalty": 0,
        "volume_penalty": 0,
        "dbt_penalty": 0
    }
    
    # 1. Create trust score
    record = TrustScoreService.save_trust_score(
        db=db_session,
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        penalties=penalties,
        trust_score=85,
        total_penalty=15,
        status="HEALTHY"
    )
    
    assert record.id is not None
    assert record.trust_score == 85
    assert record.trust_score_status == "HEALTHY"
    mock_publish.assert_called_once()
    
    # Check it exists in database
    db_record = db_session.query(TrustScore).filter_by(pipeline_run_id=run_id).first()
    assert db_record is not None
    assert db_record.contract_penalty == 10
    
    # 2. Update existing (idempotency)
    mock_publish.reset_mock()
    updated_penalties = penalties.copy()
    updated_penalties["contract_penalty"] = 20
    
    updated_record = TrustScoreService.save_trust_score(
        db=db_session,
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        penalties=updated_penalties,
        trust_score=75,
        total_penalty=25,
        status="WARNING"
    )
    
    assert updated_record.id == record.id  # Same UUID
    assert updated_record.trust_score == 75
    assert updated_record.contract_penalty == 20
    mock_publish.assert_called_once()
    
    # Verify DB contains updated row
    db_updated = db_session.query(TrustScore).filter_by(pipeline_run_id=run_id).first()
    assert db_updated.trust_score == 75


# Test 13: save_trust_score audits score changes
def test_save_trust_score_audits_large_changes(db_session, mock_publish):
    """Test that save_trust_score logs a warning when a score changes by >= 10 points."""
    run_id = uuid.uuid4()
    penalties = {
        "contract_penalty": 0,
        "anomaly_penalty": 0,
        "freshness_penalty": 0,
        "volume_penalty": 0,
        "dbt_penalty": 0
    }
    
    # Save initial score of 100
    TrustScoreService.save_trust_score(
        db=db_session,
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        penalties=penalties,
        trust_score=100,
        total_penalty=0,
        status="HEALTHY"
    )
    
    # Save updated score of 85 (shift of 15 points -> >= 10 threshold)
    with patch("backend.modules.trust_score.service.logger.warning") as mock_warn:
        TrustScoreService.save_trust_score(
            db=db_session,
            pipeline_run_id=run_id,
            table_name="bronze_financial_candles",
            penalties=penalties,
            trust_score=85,
            total_penalty=15,
            status="HEALTHY"
        )
        mock_warn.assert_any_call(
            "Significant trust score change detected for pipeline run: "
            f"{run_id}. Previous score: 100, New score: 85 (Difference: 15).",
            extra={
                "pipeline_run_id": str(run_id),
                "previous_score": 100,
                "new_score": 85,
                "difference": 15
            }
        )


# Test 14: get_trust_score_history and pagination parameters
def test_get_trust_score_history_and_pagination(db_session):
    """Test retrieving history, pages calculation, and parameter validation."""
    table_name = "bronze_financial_candles"
    penalties = {
        "contract_penalty": 0,
        "anomaly_penalty": 0,
        "freshness_penalty": 0,
        "volume_penalty": 0,
        "dbt_penalty": 0
    }
    
    # Seed 5 runs
    for i in range(5):
        TrustScoreService.save_trust_score(
            db=db_session,
            pipeline_run_id=uuid.uuid4(),
            table_name=table_name,
            penalties=penalties,
            trust_score=90 + i,
            total_penalty=10 - i,
            status="HEALTHY"
        )
        
    # Get history with page_size=2
    res = TrustScoreService.get_trust_score_history(db_session, table_name, page=1, page_size=2)
    assert res["total"] == 5
    assert len(res["items"]) == 2
    assert res["pages"] == 3
    assert res["page"] == 1
    assert res["page_size"] == 2
    
    # Test invalid parameters
    with pytest.raises(ValueError, match="Page number must be 1 or greater"):
        TrustScoreService.get_trust_score_history(db_session, table_name, page=0)
        
    with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
        TrustScoreService.get_trust_score_history(db_session, table_name, page_size=105)


# Task 8: DBT Penalty Tests

def test_calculate_dbt_penalty_empty(db_session):
    """Test that DBT penalty is 0 when no test results exist (but table is set up)."""
    run_id = uuid.uuid4()
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["dbt_penalty"] == 0


def test_calculate_dbt_penalty_with_failures(db_session):
    """Test dbt_penalty logic with failed tests within/outside 15-minute window and caps at 20."""
    run_id = uuid.uuid4()
    run_created_at = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
    
    # Seed DBT test results
    # 1. Failed inside window (run_created_at to +15 mins)
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('1', 'fail', '2026-05-26 12:05:00')
    """))
    # 2. Failed inside window boundary
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('2', 'fail', '2026-05-26 12:15:00')
    """))
    # 3. Failed outside window (before run_created_at)
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('3', 'fail', '2026-05-26 11:59:00')
    """))
    # 4. Failed outside window (after run_created_at + 15 mins)
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('4', 'fail', '2026-05-26 12:16:00')
    """))
    # 5. Passed inside window
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('5', 'pass', '2026-05-26 12:05:00')
    """))
    db_session.commit()
    
    # 2 failures inside window * 7 = 14 penalty points
    penalties = TrustScoreService.calculate_penalties(
        db_session, run_id, "bronze_financial_candles", run_created_at=run_created_at
    )
    assert penalties["dbt_penalty"] == 14
    
    # Now add more failures to exceed the 20-point cap
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('6', 'fail', '2026-05-26 12:10:00')
    """))
    db_session.commit()
    
    # 3 failures inside window * 7 = 21 -> capped at 20
    penalties = TrustScoreService.calculate_penalties(
        db_session, run_id, "bronze_financial_candles", run_created_at=run_created_at
    )
    assert penalties["dbt_penalty"] == 20


def test_calculate_dbt_penalty_graceful_degradation(db_session):
    """Test that calculate_penalties gracefully defaults DBT penalty to 0 when table/schema does not exist."""
    db_session.execute(text("DROP TABLE test_results.dbt_test_results"))
    db_session.commit()
    
    run_id = uuid.uuid4()
    with patch("backend.modules.trust_score.service.logger.info") as mock_logger:
        penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
        assert penalties["dbt_penalty"] == 0
        mock_logger.assert_called()


# Task 9: Freshness Penalty Tests

def test_calculate_freshness_penalty_no_baseline(db_session):
    """Test that freshness penalty is 0 when no baseline exists for the metric."""
    from backend.modules.anomaly.models import SilverAnomalyFeature
    run_id = uuid.uuid4()
    
    # Seed feature record only
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=100,
        null_rates={},
        freshness_latency_seconds=120.0,
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(feature)
    db_session.commit()
    
    with patch("backend.modules.trust_score.service.logger.warning") as mock_warn:
        penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
        assert penalties["freshness_penalty"] == 0
        mock_warn.assert_any_call(
            "Baseline missing for metric 'freshness_latency_seconds'; defaulting to 0 freshness penalty",
            extra={"pipeline_run_id": str(run_id), "table_name": "bronze_financial_candles"}
        )


def test_calculate_freshness_penalty_with_baseline(db_session):
    """Test that freshness penalty is calculated correctly based on Z-score deviation from baseline."""
    from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature
    run_id = uuid.uuid4()
    
    # Mean = 50, std_dev = 10
    baseline = AnomalyBaseline(
        id=uuid.uuid4(),
        table_name="bronze_financial_candles",
        metric_name="freshness_latency_seconds",
        feature_columns=[],
        mean=50.0,
        std_dev=10.0
    )
    # Value = 65 -> deviation = 15 -> z-score = 1.5 -> penalty = 1.5 * (30/3) = 15
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=100,
        null_rates={},
        freshness_latency_seconds=65.01,
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(baseline)
    db_session.add(feature)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["freshness_penalty"] == 15


def test_calculate_freshness_penalty_capped_at_max(db_session):
    """Test that freshness penalty is correctly capped at 30 even with extreme Z-score."""
    from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature
    run_id = uuid.uuid4()
    
    baseline = AnomalyBaseline(
        id=uuid.uuid4(),
        table_name="bronze_financial_candles",
        metric_name="freshness_latency_seconds",
        feature_columns=[],
        mean=50.0,
        std_dev=10.0
    )
    # Value = 150 -> deviation = 100 -> z-score = 10.0 -> penalty = 10 * 10 = 100 -> capped at 30
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=100,
        null_rates={},
        freshness_latency_seconds=150.0,
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(baseline)
    db_session.add(feature)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["freshness_penalty"] == 30


# Task 10: Volume Penalty Tests

def test_calculate_volume_penalty_no_baseline(db_session):
    """Test that volume penalty is 0 when no baseline exists for row count."""
    from backend.modules.anomaly.models import SilverAnomalyFeature
    run_id = uuid.uuid4()
    
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=1500,
        null_rates={},
        freshness_latency_seconds=10.0,
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(feature)
    db_session.commit()
    
    with patch("backend.modules.trust_score.service.logger.warning") as mock_warn:
        penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
        assert penalties["volume_penalty"] == 0
        mock_warn.assert_any_call(
            "Baseline missing for metric 'row_count'; defaulting to 0 volume penalty",
            extra={"pipeline_run_id": str(run_id), "table_name": "bronze_financial_candles"}
        )


def test_calculate_volume_penalty_with_baseline(db_session):
    """Test that volume penalty is calculated correctly based on row count Z-score deviation."""
    from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature
    run_id = uuid.uuid4()
    
    # Mean = 1000, std_dev = 100
    baseline = AnomalyBaseline(
        id=uuid.uuid4(),
        table_name="bronze_financial_candles",
        metric_name="row_count",
        feature_columns=[],
        mean=1000.0,
        std_dev=100.0
    )
    # Value = 1150 -> deviation = 150 -> z-score = 1.5 -> penalty = 1.5 * (30/3) = 15
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=1151,
        null_rates={},
        freshness_latency_seconds=10.0,
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(baseline)
    db_session.add(feature)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["volume_penalty"] == 15


def test_calculate_volume_penalty_capped_at_max(db_session):
    """Test that volume penalty is capped at 30 for extreme row count deviations."""
    from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature
    run_id = uuid.uuid4()
    
    baseline = AnomalyBaseline(
        id=uuid.uuid4(),
        table_name="bronze_financial_candles",
        metric_name="row_count",
        feature_columns=[],
        mean=1000.0,
        std_dev=100.0
    )
    # Value = 2000 -> deviation = 1000 -> z-score = 10.0 -> penalty = 100 -> capped at 30
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=2000,
        null_rates={},
        freshness_latency_seconds=10.0,
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(baseline)
    db_session.add(feature)
    db_session.commit()
    
    penalties = TrustScoreService.calculate_penalties(db_session, run_id, "bronze_financial_candles")
    assert penalties["volume_penalty"] == 30


# Task 11: End-to-End Trust Score Test

def test_calculate_trust_score_with_all_penalties(db_session):
    """Test full calculation logic aggregating contract, anomaly, freshness, volume, and dbt penalties."""
    from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature
    run_id = uuid.uuid4()
    run_created_at = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
    
    # 1. Seed contract and violation (1 violation with penalty 10)
    contract = Contract(
        id=uuid.uuid4(),
        name="test_e2e_contract",
        table_name="bronze_financial_candles",
        version=1,
        schema_definition={},
        is_active=True,
        created_at=run_created_at,
        updated_at=run_created_at
    )
    db_session.add(contract)
    db_session.commit()
    db_session.refresh(contract)
    
    violation = ContractViolation(
        id=uuid.uuid4(),
        contract_id=contract.id,
        pipeline_run_id=run_id,
        column_name="close_price",
        violation_type="null_value",
        penalty_amount=10,
        description="Null close_price",
        created_at=run_created_at
    )
    db_session.add(violation)
    
    # 2. Seed anomaly (1 anomaly with penalty 15)
    anomaly = AnomalyDetection(
        id=uuid.uuid4(),
        pipeline_run_id=run_id,
        table_name="bronze_financial_candles",
        anomaly_type="price_anomaly",
        anomaly_score=0.8,
        anomaly_penalty=15,
        is_false_positive=False,
        explanation="Abnormal price spike",
        created_at=run_created_at,
        updated_at=run_created_at
    )
    db_session.add(anomaly)
    
    # 3. Seed DBT failures (2 failures inside window * 7 = 14)
    db_session.execute(text("""
        INSERT INTO test_results.dbt_test_results (id, status, execution_completed_at)
        VALUES ('e2e_1', 'fail', '2026-05-26 12:05:00'),
               ('e2e_2', 'fail', '2026-05-26 12:10:00')
    """))
    
    # 4. Seed freshness baseline and feature (Z-score 1.5 -> penalty 15)
    freshness_base = AnomalyBaseline(
        id=uuid.uuid4(),
        table_name="bronze_financial_candles",
        metric_name="freshness_latency_seconds",
        feature_columns=[],
        mean=100.0,
        std_dev=20.0
    )
    db_session.add(freshness_base)
    
    # 5. Seed volume baseline and feature (Z-score 1.5 -> penalty 15)
    volume_base = AnomalyBaseline(
        id=uuid.uuid4(),
        table_name="bronze_financial_candles",
        metric_name="row_count",
        feature_columns=[],
        mean=500.0,
        std_dev=50.0
    )
    db_session.add(volume_base)
    
    feature = SilverAnomalyFeature(
        pipeline_run_id=run_id,
        source_name="finnhub",
        row_count=424,  # Deviation 76 / std_dev 50 = 1.52 Z-score -> penalty 15
        null_rates={},
        freshness_latency_seconds=130.1,  # Deviation 30.1 / std_dev 20 = 1.505 Z-score -> penalty 15
        run_timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(feature)
    db_session.commit()
    
    # Calculate
    penalties = TrustScoreService.calculate_penalties(
        db_session, run_id, "bronze_financial_candles", run_created_at=run_created_at
    )
    
    assert penalties["contract_penalty"] == 10
    assert penalties["anomaly_penalty"] == 15
    assert penalties["dbt_penalty"] == 14
    assert penalties["freshness_penalty"] == 15
    assert penalties["volume_penalty"] == 15
    
    score, total_penalty, status = TrustScoreService.calculate_trust_score(penalties)
    
    assert total_penalty == 69
    assert score == 31
    assert status == "CRITICAL"
