from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class AppSettingsResponse(BaseModel):
    cors_origins: List[str] = ["http://localhost:5173"]
    data_retention_days: int = 90
    incident_threshold: int = 70
    global_webhook_url: Optional[str] = None

class AppSettingsUpdate(BaseModel):
    cors_origins: Optional[List[str]] = None
    data_retention_days: Optional[int] = None
    incident_threshold: Optional[int] = None
    global_webhook_url: Optional[str] = None

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    expires_in_days: Optional[int] = None

class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Only returned once on creation
    key_preview: str
    permissions: Optional[List[str]] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_preview: str
    permissions: Optional[List[str]] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IntegrationConnectionRequest(BaseModel):
    name: str
    provider: str  # SNOWFLAKE, BIGQUERY, POSTGRESQL, AIRFLOW
    config: Dict[str, Any]  # Key-value config details (credentials, connection settings)
    is_active: bool = True

class IntegrationConnectionResponse(BaseModel):
    id: UUID
    name: str
    provider: str
    is_active: bool
    config_preview: Dict[str, Any]  # Sensitive fields masked
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class IntegrationTestResponse(BaseModel):
    success: bool
    message: str


class SensitivityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PipelineFrequencySettings(BaseModel):
    pipeline_name: str
    run_frequency_minutes: int = Field(15, ge=1)
    alert_frequency_minutes: int = Field(30, ge=1)
    anomaly_immediate_alert: bool = True
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    severity_overrides: Dict[str, int] = Field(default_factory=lambda: {
        "CRITICAL": 1,
        "HIGH": 5,
        "MEDIUM": 15,
        "LOW": 60
    })

