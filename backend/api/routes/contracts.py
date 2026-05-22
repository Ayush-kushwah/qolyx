import uuid
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.modules.contracts.models import Contract, ContractViolation
from backend.modules.contracts.schemas import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractViolationResponse,
    GenerateContractRequest,
    GenerateContractResponse,
)
from backend.modules.contracts import services as contract_services

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=List[ContractResponse])
def list_contracts(db: Session = Depends(get_db)) -> List[ContractResponse]:
    """Retrieve all contracts stored in the database."""
    contracts = db.query(Contract).all()
    return [ContractResponse.model_validate(c) for c in contracts]


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(contract_id: uuid.UUID, db: Session = Depends(get_db)) -> ContractResponse:
    """Retrieve a single contract by its unique ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with ID {contract_id} not found"
        )
    return ContractResponse.model_validate(contract)


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db)) -> ContractResponse:
    """Create a new data contract manually."""
    existing = db.query(Contract).filter(Contract.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contract with name '{payload.name}' already exists"
        )

    schema_dict = {
        col_name: {
            "data_type": expectation.data_type,
            "nullable": expectation.nullable,
            "max_length": expectation.max_length,
            "is_required": expectation.is_required,
        }
        for col_name, expectation in payload.schema_definition.items()
    }

    contract = Contract(
        name=payload.name,
        table_name=payload.table_name,
        schema_definition=schema_dict,
        is_active=payload.is_active,
        version=1,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return ContractResponse.model_validate(contract)


@router.put("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: uuid.UUID,
    payload: ContractUpdate,
    db: Session = Depends(get_db)
) -> ContractResponse:
    """Update an existing data contract, incrementing its version if schema changes."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with ID {contract_id} not found"
        )

    if payload.name is not None:
        if payload.name != contract.name:
            existing = db.query(Contract).filter(Contract.name == payload.name).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Contract with name '{payload.name}' already exists"
                )
        contract.name = payload.name

    if payload.table_name is not None:
        contract.table_name = payload.table_name

    if payload.schema_definition is not None:
        schema_dict = {
            col_name: {
                "data_type": expectation.data_type,
                "nullable": expectation.nullable,
                "max_length": expectation.max_length,
                "is_required": expectation.is_required,
            }
            for col_name, expectation in payload.schema_definition.items()
        }
        contract.schema_definition = schema_dict
        contract.version += 1

    if payload.is_active is not None:
        contract.is_active = payload.is_active

    db.commit()
    db.refresh(contract)
    return ContractResponse.model_validate(contract)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Delete a contract from the database."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with ID {contract_id} not found"
        )
    db.delete(contract)
    db.commit()
    return None


@router.post("/generate", response_model=GenerateContractResponse)
def generate_contract(
    payload: GenerateContractRequest,
    db: Session = Depends(get_db)
) -> GenerateContractResponse:
    """Generate a proposal contract schema definition from an existing table structure."""
    try:
        return contract_services.generate_contract_from_table(
            db=db,
            table_name=payload.table_name,
            name=payload.name
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.get("/violations/run/{pipeline_run_id}", response_model=List[ContractViolationResponse])
def get_violations_for_run(
    pipeline_run_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> List[ContractViolationResponse]:
    """Retrieve all logged violations for a specific pipeline execution run."""
    violations = contract_services.get_violations_for_run(db, pipeline_run_id)
    return [ContractViolationResponse.model_validate(v) for v in violations]


@router.get("/penalty/run/{pipeline_run_id}", response_model=Dict[str, object])
def get_penalty_for_run(
    pipeline_run_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Dict[str, object]:
    """Get the total penalty score calculated for a specific pipeline execution run."""
    penalty = contract_services.get_total_penalty_for_run(db, pipeline_run_id)
    return {
        "pipeline_run_id": pipeline_run_id,
        "total_penalty": penalty,
    }


@router.post("/initialize", response_model=List[ContractResponse])
def initialize_default_contracts(db: Session = Depends(get_db)) -> List[ContractResponse]:
    """Initialize/seed default contracts for core bronze tables if they do not exist."""
    contracts = contract_services.initialize_contracts(db)
    return [ContractResponse.model_validate(c) for c in contracts]
