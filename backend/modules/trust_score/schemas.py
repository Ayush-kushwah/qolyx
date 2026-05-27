import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TrustScoreResponse(BaseModel):
    """Pydantic model representing a complete TrustScore database record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique database identifier for the trust score record")
    pipeline_run_id: uuid.UUID = Field(..., description="The unique run identifier of the ingestion pipeline")
    table_name: str = Field(..., description="Name of the ingestion table evaluated")
    contract_penalty: int = Field(..., description="Penalty score from contract violations")
    freshness_penalty: int = Field(..., description="Penalty score from freshness latency")
    volume_penalty: int = Field(..., description="Penalty score from volume changes")
    anomaly_penalty: int = Field(..., description="Penalty score from anomaly detections")
    dbt_penalty: int = Field(..., description="Penalty score from dbt run test failures")
    total_penalty: int = Field(..., description="Total combined capped penalty score")
    trust_score: int = Field(..., description="Calculated trust score (100 - total_penalty)")
    trust_score_status: str = Field(..., description="Status health classification (HEALTHY, WARNING, DEGRADED, CRITICAL)")
    created_at: datetime = Field(..., description="Timestamp when the trust score was calculated")
    updated_at: datetime = Field(..., description="Timestamp when the trust score record was last updated")


class TrustScoreCreate(BaseModel):
    """Pydantic model for validating inputs when creating/updating a trust score."""
    model_config = ConfigDict(frozen=True)

    pipeline_run_id: uuid.UUID = Field(..., description="The unique run identifier of the ingestion pipeline")
    table_name: str = Field(..., description="Name of the ingestion table evaluated")
    contract_penalty: Optional[int] = Field(0, description="Penalty score from contract violations")
    freshness_penalty: Optional[int] = Field(0, description="Penalty score from freshness latency")
    volume_penalty: Optional[int] = Field(0, description="Penalty score from volume changes")
    anomaly_penalty: Optional[int] = Field(0, description="Penalty score from anomaly detections")
    dbt_penalty: Optional[int] = Field(0, description="Penalty score from dbt run test failures")


class TrustScoreAggregatedResponse(BaseModel):
    """Pydantic model representing the aggregated trust score along with penalty breakdown."""
    model_config = ConfigDict(from_attributes=True)

    pipeline_run_id: uuid.UUID = Field(..., description="The unique run identifier of the ingestion pipeline")
    table_name: str = Field(..., description="Name of the ingestion table evaluated")
    trust_score: int = Field(..., description="Calculated trust score (100 - total_penalty)")
    total_penalty: int = Field(..., description="Total combined capped penalty score")
    trust_score_status: str = Field(..., description="Status health classification (HEALTHY, WARNING, DEGRADED, CRITICAL)")
    breakdown: Dict[str, int] = Field(..., description="Breakdown dictionary containing all five individual penalty values")


class TrustScoreHistoryResponse(BaseModel):
    """Pydantic model representing a paginated history list of trust score responses."""
    model_config = ConfigDict(from_attributes=True)

    items: List[TrustScoreResponse] = Field(..., description="List of historical trust score records")
    total: int = Field(..., description="Total number of records matching the query")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages available")
