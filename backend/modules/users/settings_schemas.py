from pydantic import BaseModel, Field
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
