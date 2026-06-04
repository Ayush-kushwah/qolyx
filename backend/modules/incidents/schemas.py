import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class IncidentTimelineResponse(BaseModel):
    """Pydantic schema representing an incident timeline event."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: datetime


class IncidentCommentRequest(BaseModel):
    """Pydantic schema representing a request to add a comment."""
    model_config = ConfigDict(frozen=True)

    comment: str = Field(..., min_length=1)
    created_by: str = Field(..., min_length=1)


class IncidentCommentResponse(BaseModel):
    """Pydantic schema representing an incident comment."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    comment: str
    created_by: str
    created_at: datetime


class IncidentRCAGenerateRequest(BaseModel):
    """Pydantic schema representing a request to manually regenerate RCA."""
    model_config = ConfigDict(frozen=True)

    incident_id: uuid.UUID


class IncidentRCAResponse(BaseModel):
    """Pydantic schema representing incident Root Cause Analysis (RCA) details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    version: int
    summary: str
    root_cause: str
    contributing_factors: Optional[List[str]] = None
    recommendation: Optional[str] = None
    primary_penalty: str
    confidence: float
    generated_at: datetime


class IncidentCreate(BaseModel):
    """Pydantic schema representing a request to create a new incident."""
    model_config = ConfigDict(frozen=True)

    trust_score_id: Optional[uuid.UUID] = None
    pipeline_run_id: uuid.UUID
    table_name: str
    severity: str
    title: str
    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None


class IncidentResponse(BaseModel):
    """Pydantic schema representing the complete incident response payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trust_score_id: Optional[uuid.UUID] = None
    pipeline_run_id: uuid.UUID
    table_name: str
    severity: str
    state: str
    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    escalated_at: Optional[datetime] = None
    escalation_level: int
    muted_until: Optional[datetime] = None

    timeline: Optional[List[IncidentTimelineResponse]] = None
    comments: Optional[List[IncidentCommentResponse]] = None
    rca: Optional[IncidentRCAResponse] = None


class IncidentUpdate(BaseModel):
    """Pydantic schema representing a request to update an existing incident."""
    model_config = ConfigDict(frozen=True)

    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None
    resolution_notes: Optional[str] = None
    state: Optional[str] = None


class AlertConfigCreate(BaseModel):
    """Pydantic schema representing a request to create an alert config."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    channel_type: str = Field(..., description="slack, discord, teams, telegram, email, webhook")
    webhook_url: Optional[str] = None
    email_config: Optional[Dict[str, Any]] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    severity_threshold: str = "MEDIUM"
    is_active: bool = True


class AlertConfigResponse(BaseModel):
    """Pydantic schema representing an alert config response payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    channel_type: str
    webhook_url: Optional[str] = None
    email_config: Optional[Dict[str, Any]] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    severity_threshold: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AlertConfigUpdate(BaseModel):
    """Pydantic schema representing a request to update an alert config."""
    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    channel_type: Optional[str] = None
    webhook_url: Optional[str] = None
    email_config: Optional[Dict[str, Any]] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    severity_threshold: Optional[str] = None
    is_active: Optional[bool] = None


class AlertTestRequest(BaseModel):
    """Pydantic schema representing a request to test alert channel."""
    model_config = ConfigDict(frozen=True)

    channel_type: str
    message: str


class OncallRotationCreate(BaseModel):
    """Pydantic schema representing a request to create an on-call rotation."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    team_name: str = Field(..., min_length=1)
    members: List[str] = Field(..., min_items=1)
    rotation_type: str = Field(..., description="DAILY, WEEKLY, HOURLY")


class OncallRotationResponse(BaseModel):
    """Pydantic schema representing an on-call rotation response payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    team_name: str
    members: List[str]
    current_index: int
    rotation_type: str
    last_rotated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class EscalationPolicyCreate(BaseModel):
    """Pydantic schema representing a request to create an escalation policy."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    timeout_minutes: int = Field(..., ge=1)
    target_type: str = Field(..., description="TEAM, MEMBER, ROTATION, SLACK_CHANNEL")
    target_identifier: str = Field(..., min_length=1)


class EscalationPolicyResponse(BaseModel):
    """Pydantic schema representing an escalation policy response payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    severity: str
    timeout_minutes: int
    target_type: str
    target_identifier: str
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    """Pydantic schema representing a paginated list of incidents."""
    model_config = ConfigDict(from_attributes=True)

    items: List[IncidentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class IncidentStatsResponse(BaseModel):
    """Pydantic schema representing summary statistics of incidents."""
    model_config = ConfigDict(frozen=True)

    by_severity: Dict[str, int]
    by_state: Dict[str, int]
    total_open: int
    total_acknowledged: int
    total_resolved: int
    total_closed: int
