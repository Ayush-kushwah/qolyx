import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ColumnExpectation(BaseModel):
    """Expectations for a single column in a schema contract."""
    model_config = ConfigDict(frozen=True)

    data_type: str = Field(
        ...,
        description="The expected data type of the column (e.g., 'string', 'integer', 'float', 'boolean', 'datetime', 'json')."
    )
    nullable: bool = Field(
        True,
        description="Whether the column is allowed to contain null values."
    )
    max_length: Optional[int] = Field(
        None,
        description="The maximum allowed character length of string values."
    )
    is_required: bool = Field(
        True,
        description="Whether the column is required to exist in the schema."
    )


class ContractCreate(BaseModel):
    """Schema representing a request to create a new data contract."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(
        ...,
        description="A unique, human-readable name for the contract."
    )
    table_name: str = Field(
        ...,
        description="The physical database table name this contract applies to."
    )
    schema_definition: Dict[str, ColumnExpectation] = Field(
        ...,
        description="A mapping of column names to their data type and nullability constraints."
    )
    is_active: bool = Field(
        True,
        description="Flag indicating if the contract is active and should be evaluated."
    )


class ContractUpdate(BaseModel):
    """Schema representing a request to update an existing data contract."""
    model_config = ConfigDict(frozen=True)

    name: Optional[str] = Field(
        None,
        description="A unique, human-readable name for the contract."
    )
    table_name: Optional[str] = Field(
        None,
        description="The physical database table name this contract applies to."
    )
    schema_definition: Optional[Dict[str, ColumnExpectation]] = Field(
        None,
        description="A mapping of column names to their data type and nullability constraints."
    )
    is_active: Optional[bool] = Field(
        None,
        description="Flag indicating if the contract is active and should be evaluated."
    )


class ContractResponse(BaseModel):
    """Schema representing the database contract entity details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the contract."
    )
    name: str = Field(
        ...,
        description="A unique, human-readable name for the contract."
    )
    table_name: str = Field(
        ...,
        description="The physical database table name this contract applies to."
    )
    version: int = Field(
        ...,
        description="The sequential version identifier of this contract."
    )
    schema_definition: Dict[str, ColumnExpectation] = Field(
        ...,
        description="A mapping of column names to their data type and nullability constraints."
    )
    is_active: bool = Field(
        ...,
        description="Flag indicating if the contract is active and should be evaluated."
    )
    created_at: datetime = Field(
        ...,
        description="The UTC timestamp when the contract was created."
    )
    updated_at: datetime = Field(
        ...,
        description="The UTC timestamp when the contract was last updated."
    )


class ContractViolationResponse(BaseModel):
    """Schema representing an individual contract violation record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the contract violation."
    )
    contract_id: uuid.UUID = Field(
        ...,
        description="Identifier of the associated contract."
    )
    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="Identifier of the ingestion pipeline execution run."
    )
    violation_type: str = Field(
        ...,
        description="The type of contract breach: missing_column, wrong_type, null_violation, extra_column."
    )
    column_name: Optional[str] = Field(
        None,
        description="The name of the column that caused the violation."
    )
    expected_value: Optional[str] = Field(
        None,
        description="The expected type or constraint that was breached."
    )
    actual_value: Optional[str] = Field(
        None,
        description="The actual type or value observed during validation."
    )
    penalty_amount: int = Field(
        ...,
        description="The penalty points deducted for this violation."
    )
    description: str = Field(
        ...,
        description="Plain-English diagnosis of the structural breach."
    )
    created_at: datetime = Field(
        ...,
        description="The UTC timestamp when this violation was recorded."
    )


class ContractValidationResult(BaseModel):
    """Schema representing the overall outcome of a contract validation run."""
    model_config = ConfigDict(frozen=True)

    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="Identifier of the ingestion pipeline execution run."
    )
    table_name: str = Field(
        ...,
        description="The physical database table name checked."
    )
    is_valid: bool = Field(
        ...,
        description="True if the data satisfies the contract constraints, False otherwise."
    )
    violation_count: int = Field(
        ...,
        description="Total number of violations detected."
    )
    total_penalty: int = Field(
        ...,
        description="Total accumulated trust penalty score (capped at 40)."
    )
    violations: List[ContractViolationResponse] = Field(
        ...,
        description="Detailed list of all detected violations."
    )


class GenerateContractRequest(BaseModel):
    """Schema representing a request to automatically generate a contract from an existing table."""
    model_config = ConfigDict(frozen=True)

    table_name: str = Field(
        ...,
        description="The database table name to inspect for schema auto-generation."
    )
    name: str = Field(
        ...,
        description="The name to assign to the newly auto-generated contract."
    )


class GenerateContractResponse(BaseModel):
    """Schema representing the metadata generated for a new data contract."""
    model_config = ConfigDict(frozen=True)

    table_name: str = Field(
        ...,
        description="The database table name used for schema inspection."
    )
    name: str = Field(
        ...,
        description="The name assigned to the newly auto-generated contract."
    )
    schema_definition: Dict[str, ColumnExpectation] = Field(
        ...,
        description="The inferred schema expectations containing column names, types, and nullability."
    )
