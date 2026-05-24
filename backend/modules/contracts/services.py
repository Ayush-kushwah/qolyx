import uuid
import json
import logging
from typing import Dict, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from backend.core.events import publish
from backend.core.exceptions import PipelineBlockedException
from backend.modules.contracts.models import Contract, ContractViolation

logger = logging.getLogger("qolyx.contracts.services")
from backend.modules.contracts.schemas import (
    ColumnExpectation,
    ContractValidationResult,
    ContractViolationResponse,
    GenerateContractResponse
)
from backend.modules.ingestion.models import BronzeFinancialCandle, BronzeFdaEvent, BronzeGithubEvent

MODEL_MAP = {
    "bronze_financial_candles": BronzeFinancialCandle,
    "bronze_fda_events": BronzeFdaEvent,
    "bronze_github_events": BronzeGithubEvent,
}

def _type_matches(db_type: Union[str, object], expected_type: str) -> bool:
    """Check if the physical database column type matches the expected data contract type."""
    db_type_str = str(db_type).lower()
    expected_type = expected_type.lower()

    if expected_type == "uuid":
        return "uuid" in db_type_str
    elif expected_type == "string":
        return any(t in db_type_str for t in ["varchar", "string", "text", "char"])
    elif expected_type == "integer":
        return any(t in db_type_str for t in ["int", "serial"])
    elif expected_type == "float":
        return any(t in db_type_str for t in ["float", "numeric", "double", "real"])
    elif expected_type == "boolean":
        return "bool" in db_type_str
    elif expected_type == "datetime":
        return any(t in db_type_str for t in ["timestamp", "date", "datetime"])
    elif expected_type == "json":
        return "json" in db_type_str
    return False


def _map_db_type_to_contract_type(db_type_str: str) -> str:
    """Map a raw database column type string to a contract expectation type."""
    db_type_str = db_type_str.lower()
    if "uuid" in db_type_str:
        return "uuid"
    elif any(t in db_type_str for t in ["int", "serial"]):
        return "integer"
    elif any(t in db_type_str for t in ["float", "numeric", "double", "real"]):
        return "float"
    elif "bool" in db_type_str:
        return "boolean"
    elif any(t in db_type_str for t in ["timestamp", "date", "datetime"]):
        return "datetime"
    elif "json" in db_type_str:
        return "json"
    else:
        return "string"


def validate_pipeline_run(
    db: Session,
    table_name: str,
    pipeline_run_id: uuid.UUID,
    sample_data: Optional[Dict[str, object]] = None
) -> ContractValidationResult:
    """Validate all rows for a pipeline run in a specific table against its active contract."""
    contract = db.query(Contract).filter(
        Contract.table_name == table_name,
        Contract.is_active == True
    ).order_by(Contract.version.desc()).first()

    if not contract:
        result = ContractValidationResult(
            pipeline_run_id=pipeline_run_id,
            table_name=table_name,
            is_valid=True,
            violation_count=0,
            total_penalty=0,
            violations=[]
        )
        publish("contract.validated", {
            "pipeline_run_id": str(pipeline_run_id),
            "table_name": table_name,
            "is_valid": True,
            "violation_count": 0,
            "total_penalty": 0
        })
        return result

    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        violation = ContractViolation(
            contract_id=contract.id,
            pipeline_run_id=pipeline_run_id,
            violation_type="missing_column",
            description=f"Table '{table_name}' does not exist in the database.",
            penalty_amount=10
        )
        db.add(violation)
        db.commit()
        db.refresh(violation)

        violation_resp = ContractViolationResponse.model_validate(violation)
        publish("contract.validated", {
            "pipeline_run_id": str(pipeline_run_id),
            "table_name": table_name,
            "is_valid": False,
            "violation_count": 1,
            "total_penalty": 10
        })
        return ContractValidationResult(
            pipeline_run_id=pipeline_run_id,
            table_name=table_name,
            is_valid=False,
            violation_count=1,
            total_penalty=10,
            violations=[violation_resp]
        )

    columns = inspector.get_columns(table_name)
    db_cols = {col["name"]: col for col in columns}

    schema_def = contract.schema_definition
    if isinstance(schema_def, str):
        schema_def = json.loads(schema_def)

    expectations: Dict[str, ColumnExpectation] = {}
    for col_name, val in schema_def.items():
        if isinstance(val, dict):
            expectations[col_name] = ColumnExpectation(**val)
        else:
            expectations[col_name] = val

    violations_to_create: List[ContractViolation] = []

    # Check for missing columns
    for col_name, expectation in expectations.items():
        if col_name not in db_cols:
            if expectation.is_required:
                violations_to_create.append(ContractViolation(
                    contract_id=contract.id,
                    pipeline_run_id=pipeline_run_id,
                    violation_type="missing_column",
                    column_name=col_name,
                    expected_value=expectation.data_type,
                    actual_value=None,
                    penalty_amount=10,
                    description=f"Required column '{col_name}' is missing from database table '{table_name}'."
                ))

    # Check for extra columns
    for db_col_name in db_cols.keys():
        if db_col_name not in expectations:
            violations_to_create.append(ContractViolation(
                contract_id=contract.id,
                pipeline_run_id=pipeline_run_id,
                violation_type="extra_column",
                column_name=db_col_name,
                expected_value=None,
                actual_value=str(db_cols[db_col_name]["type"]),
                penalty_amount=10,
                description=f"Undocumented column '{db_col_name}' found in database table '{table_name}'."
            ))

    # Check for wrong type
    for col_name, expectation in expectations.items():
        if col_name in db_cols:
            db_col = db_cols[col_name]
            if not _type_matches(db_col["type"], expectation.data_type):
                violations_to_create.append(ContractViolation(
                    contract_id=contract.id,
                    pipeline_run_id=pipeline_run_id,
                    violation_type="wrong_type",
                    column_name=col_name,
                    expected_value=expectation.data_type,
                    actual_value=str(db_col["type"]),
                    penalty_amount=10,
                    description=f"Column '{col_name}' expects type '{expectation.data_type}' but database has type '{db_col['type']}'."
                ))

    # Fetch rows to check nullability and max_length
    model_cls = MODEL_MAP.get(table_name)
    if model_cls:
        rows = db.query(model_cls).filter(model_cls.pipeline_run_id == pipeline_run_id).all()
        null_flagged_cols = set()
        len_flagged_cols = set()

        for row in rows:
            for col_name, expectation in expectations.items():
                if not hasattr(row, col_name):
                    continue
                val = getattr(row, col_name)

                # Null check
                if val is None:
                    if (expectation.is_required or not expectation.nullable) and col_name not in null_flagged_cols:
                        violations_to_create.append(ContractViolation(
                            contract_id=contract.id,
                            pipeline_run_id=pipeline_run_id,
                            violation_type="null_violation",
                            column_name=col_name,
                            expected_value="NOT NULL",
                            actual_value="NULL",
                            penalty_amount=10,
                            description=f"Null value violating constraints found in column '{col_name}'."
                        ))
                        null_flagged_cols.add(col_name)

                # Max length check
                elif isinstance(val, str) and expectation.max_length is not None:
                    if len(val) > expectation.max_length and col_name not in len_flagged_cols:
                        violations_to_create.append(ContractViolation(
                            contract_id=contract.id,
                            pipeline_run_id=pipeline_run_id,
                            violation_type="wrong_type",
                            column_name=col_name,
                            expected_value=f"length <= {expectation.max_length}",
                            actual_value=f"length == {len(val)}",
                            penalty_amount=10,
                            description=f"Column '{col_name}' exceeds maximum allowed character length of {expectation.max_length} (actual length: {len(val)})."
                        ))
                        len_flagged_cols.add(col_name)

    # Save to DB
    if violations_to_create:
        for violation in violations_to_create:
            db.add(violation)
        db.commit()
        for violation in violations_to_create:
            db.refresh(violation)

    # Read violations back
    all_violations = db.query(ContractViolation).filter(
        ContractViolation.pipeline_run_id == pipeline_run_id
    ).all()

    violation_count = len(all_violations)
    total_penalty = min(violation_count * 10, 40)
    is_valid = violation_count == 0

    violations_resp = [ContractViolationResponse.model_validate(v) for v in all_violations]

    publish("contract.validated", {
        "pipeline_run_id": str(pipeline_run_id),
        "table_name": table_name,
        "is_valid": is_valid,
        "violation_count": violation_count,
        "total_penalty": total_penalty
    })

    return ContractValidationResult(
        pipeline_run_id=pipeline_run_id,
        table_name=table_name,
        is_valid=is_valid,
        violation_count=violation_count,
        total_penalty=total_penalty,
        violations=violations_resp
    )


def generate_contract_from_table(db: Session, table_name: str, name: str) -> GenerateContractResponse:
    """Generate a proposal contract schema definition from an existing database table's metadata."""
    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        raise ValueError(f"Table '{table_name}' does not exist in the database.")

    columns = inspector.get_columns(table_name)
    schema_definition: Dict[str, ColumnExpectation] = {}

    for col in columns:
        col_name = col["name"]
        db_type = col["type"]
        nullable = col.get("nullable", True)

        contract_type = _map_db_type_to_contract_type(str(db_type))
        max_length = getattr(db_type, "length", None)
        is_required = not nullable

        schema_definition[col_name] = ColumnExpectation(
            data_type=contract_type,
            nullable=nullable,
            max_length=max_length,
            is_required=is_required
        )

    return GenerateContractResponse(
        table_name=table_name,
        name=name,
        schema_definition=schema_definition
    )


def initialize_contracts(db: Session) -> List[Contract]:
    """Seed / initialize default contracts if they do not already exist in the database."""
    from backend.modules.contracts.contract_definitions import ALL_CONTRACTS
    initialized: List[Contract] = []

    for def_contract in ALL_CONTRACTS:
        existing = db.query(Contract).filter(
            Contract.name == def_contract.name
        ).first()

        if not existing:
            schema_dict = {
                col_name: {
                    "data_type": expectation.data_type,
                    "nullable": expectation.nullable,
                    "max_length": expectation.max_length,
                    "is_required": expectation.is_required
                }
                for col_name, expectation in def_contract.schema_definition.items()
            }
            contract = Contract(
                name=def_contract.name,
                table_name=def_contract.table_name,
                version=1,
                schema_definition=schema_dict,
                is_active=def_contract.is_active
            )
            db.add(contract)
            initialized.append(contract)
        else:
            initialized.append(existing)

    if initialized:
        db.commit()
        for contract in initialized:
            db.refresh(contract)

    return initialized


def get_violations_for_run(db: Session, pipeline_run_id: uuid.UUID) -> List[ContractViolation]:
    """Retrieve all stored violations for a specific pipeline run."""
    return db.query(ContractViolation).filter(ContractViolation.pipeline_run_id == pipeline_run_id).all()


def get_total_penalty_for_run(db: Session, pipeline_run_id: uuid.UUID) -> int:
    """Calculate the total contract violations trust penalty for a pipeline run, capped at 40 points."""
    violations_count = db.query(ContractViolation).filter(ContractViolation.pipeline_run_id == pipeline_run_id).count()
    return min(violations_count * 10, 40)


def enforce_pipeline_gate(
    db: Session, 
    pipeline_run_id: uuid.UUID
) -> None:
    """Checks contract violations and raises 
    PipelineBlockedException if any exist.
    Called after validation completes.
    
    Raises:
        PipelineBlockedException: if violations exist
    """
    violations = get_violations_for_run(db, pipeline_run_id)
    if violations:
        total_penalty = get_total_penalty_for_run(
            db, pipeline_run_id)
        logger.error(
            "Pipeline BLOCKED due to contract violations",
            extra={
                "pipeline_run_id": str(pipeline_run_id),
                "violations_count": len(violations),
                "total_penalty": total_penalty
            }
        )
        raise PipelineBlockedException(
            f"Pipeline BLOCKED: {len(violations)} contract "
            f"violations detected. Total penalty: "
            f"{total_penalty}/40.",
            details={
                "pipeline_run_id": str(pipeline_run_id),
                "violations_count": len(violations),
                "total_penalty": total_penalty
            }
        )
