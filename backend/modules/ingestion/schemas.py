import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

class IngestionRunRequest(BaseModel):
    """Schema representing a request to execute data ingestion for a specific data source."""
    source_name: str = Field(
        ...,
        description="The name of the external data source to ingest (e.g., 'finnhub', 'fda', 'github')."
    )

class BronzeFinancialCandleResponse(BaseModel):
    """Schema representing a record from the bronze_financial_candles table."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the financial candle record."
    )
    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="Identifier of the ingestion pipeline execution run."
    )
    symbol: str = Field(
        ...,
        description="The stock ticker symbol (e.g., 'AAPL', 'MSFT')."
    )
    open_price: Optional[float] = Field(
        None,
        description="Open price of the candle interval."
    )
    high_price: Optional[float] = Field(
        None,
        description="High price achieved during the candle interval."
    )
    low_price: Optional[float] = Field(
        None,
        description="Low price reached during the candle interval."
    )
    close_price: Optional[float] = Field(
        None,
        description="Close price of the candle interval."
    )
    volume: Optional[int] = Field(
        None,
        description="Volume of shares traded during the candle interval."
    )
    candle_timestamp: datetime = Field(
        ...,
        description="The timestamp marking the start of the stock candle."
    )
    ingested_at: datetime = Field(
        ...,
        description="The UTC timestamp when this record was written to the Bronze layer."
    )

class BronzeFdaEventResponse(BaseModel):
    """Schema representing a record from the bronze_fda_events table."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the FDA adverse event record."
    )
    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="Identifier of the ingestion pipeline execution run."
    )
    receipt_date: Optional[str] = Field(
        None,
        description="The receipt date of the adverse drug event report (formatted as YYYYMMDD)."
    )
    serious: Optional[str] = Field(
        None,
        description="Seriousness code of the event (e.g., '1' for serious, '2' for non-serious)."
    )
    reporter_country: Optional[str] = Field(
        None,
        description="Two-letter ISO country code representing the reporter's country."
    )
    drug_name: Optional[str] = Field(
        None,
        description="The medicinal product/drug name reported as primary suspect."
    )
    reaction_description: Optional[str] = Field(
        None,
        description="The MedDRA term describing the adverse drug reaction."
    )
    seriousness_hospitalization: Optional[str] = Field(
        None,
        description="Indicator showing if the adverse event resulted in hospitalization."
    )
    raw_payload: Dict[str, Any] = Field(
        ...,
        description="The complete, unaltered JSON payload fetched from openFDA."
    )
    ingested_at: datetime = Field(
        ...,
        description="The UTC timestamp when this record was written to the Bronze layer."
    )

class BronzeGithubEventResponse(BaseModel):
    """Schema representing a record from the bronze_github_events table."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the GitHub event record in the database."
    )
    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="Identifier of the ingestion pipeline execution run."
    )
    event_id: str = Field(
        ...,
        description="The original GitHub platform event identifier (string)."
    )
    event_type: str = Field(
        ...,
        description="The type of event (e.g., 'PushEvent', 'PullRequestEvent')."
    )
    actor_login: Optional[str] = Field(
        None,
        description="The login name of the GitHub user who initiated the event."
    )
    repo_name: Optional[str] = Field(
        None,
        description="The name of the target repository (formatted as org/repo)."
    )
    payload_action: Optional[str] = Field(
        None,
        description="The specific action triggered (e.g., 'opened', 'closed') if present in event payload."
    )
    created_at: Optional[datetime] = Field(
        None,
        description="The UTC timestamp when the event was originally created on GitHub."
    )
    raw_payload: Dict[str, Any] = Field(
        ...,
        description="The complete, unaltered JSON event payload downloaded from GH Archive."
    )
    ingested_at: datetime = Field(
        ...,
        description="The UTC timestamp when this record was written to the Bronze layer."
    )

class IngestionRunResponse(BaseModel):
    """Schema representing the status and outcome response of an ingestion pipeline run."""
    model_config = ConfigDict(from_attributes=True)

    pipeline_run_id: str = Field(
        ...,
        description="The unique tracking ID assigned to this ingestion run."
    )
    source_name: str = Field(
        ...,
        description="The name of the data source ingested (e.g., 'finnhub', 'fda', 'github')."
    )
    dataset_id: str = Field(
        ...,
        description="The standard dataset identifier (formatted as datasource.schema.table)."
    )
    records_ingested: int = Field(
        ...,
        description="The count of records successfully parsed and persisted to the Bronze layer."
    )
    status: str = Field(
        ...,
        description="The operational status of the run (e.g., 'success', 'failed')."
    )
    started_at: datetime = Field(
        ...,
        description="The UTC timestamp when the ingestion run commenced."
    )
