import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Boolean,
    ForeignKey,
    Text,
    Float,
    Index,
    UniqueConstraint,
    desc,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base


class Incident(Base):
    """Database model representing a data reliability incident."""

    __tablename__ = "incidents"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trust_score_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("trust_scores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, index=True)
    table_name: Any = Column(String(255), nullable=False, index=True)
    severity: Any = Column(String(20), nullable=False, index=True)
    state: Any = Column(String(20), nullable=False, default="OPEN", index=True)
    assigned_to: Any = Column(String(255), nullable=True)
    assigned_team: Any = Column(String(255), nullable=True)
    title: Any = Column(String(500), nullable=False)
    created_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    acknowledged_at: Any = Column(DateTime, nullable=True)
    resolved_at: Any = Column(DateTime, nullable=True)
    closed_at: Any = Column(DateTime, nullable=True)
    resolution_notes: Any = Column(Text, nullable=True)
    escalated_at: Any = Column(DateTime, nullable=True)
    escalation_level: Any = Column(Integer, nullable=False, default=0)
    muted_until: Any = Column(DateTime, nullable=True)

    __table_args__: Any = (
        Index(
            "idx_incidents_severity_state_created",
            "severity",
            "state",
            "created_at",
        ),
    )

    # Relationships
    timeline = relationship(
        "IncidentTimeline",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="desc(IncidentTimeline.created_at)",
        uselist=True,
    )
    comments = relationship(
        "IncidentComment",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="asc(IncidentComment.created_at)",
        uselist=True,
    )
    rcas = relationship(
        "IncidentRCA",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="desc(IncidentRCA.version)",
        uselist=True,
    )

    @property
    def rca(self) -> Any:
        """Property to return the latest RCA details for the incident."""
        return self.rcas[0] if self.rcas else None


class IncidentTimeline(Base):
    """Database model representing an event timeline entry for an incident."""

    __tablename__ = "incident_timeline"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Any = Column(String(50), nullable=False)
    event_data: Any = Column(JSON, nullable=True)
    created_by: Any = Column(String(255), nullable=True)
    created_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__: Any = (
        Index(
            "idx_incident_timeline_id_created",
            "incident_id",
            "created_at",
        ),
    )

    # Relationships
    incident: Any = relationship("Incident", back_populates="timeline")


class IncidentComment(Base):
    """Database model representing a comment on an incident."""

    __tablename__ = "incident_comments"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comment: Any = Column(Text, nullable=False)
    created_by: Any = Column(String(255), nullable=False)
    created_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    incident: Any = relationship("Incident", back_populates="comments")


class IncidentRCA(Base):
    """Database model representing the root cause analysis (RCA) of an incident."""

    __tablename__ = "incident_rcas"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Any = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Any = Column(Integer, nullable=False, default=1)
    summary: Any = Column(Text, nullable=False)
    root_cause: Any = Column(Text, nullable=False)
    contributing_factors: Any = Column(JSON, nullable=True)
    recommendation: Any = Column(Text, nullable=True)
    primary_penalty: Any = Column(String(50), nullable=False)
    confidence: Any = Column(Float, nullable=False, default=1.0)
    generated_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__: Any = (
        UniqueConstraint(
            "incident_id", "version", name="uq_incident_rca_incident_version"
        ),
    )

    # Relationships
    incident: Any = relationship("Incident", back_populates="rcas")


class AlertConfig(Base):
    """Database model representing a configured alerting channel."""

    __tablename__ = "alert_configs"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Any = Column(String(255), nullable=False)
    channel_type: Any = Column(String(20), nullable=False)
    webhook_url: Any = Column(String(500), nullable=True)
    email_config: Any = Column(JSON, nullable=True)
    telegram_bot_token: Any = Column(String(255), nullable=True)
    telegram_chat_id: Any = Column(String(255), nullable=True)
    severity_threshold: Any = Column(
        String(20), nullable=False, default="MEDIUM"
    )
    is_active: Any = Column(Boolean, nullable=False, default=True)
    created_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OncallRotation(Base):
    """Database model representing an on-call rotation schedule."""

    __tablename__ = "oncall_rotations"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Any = Column(String(255), nullable=False)
    team_name: Any = Column(String(255), nullable=False)
    members: Any = Column(JSON, nullable=False)
    current_index: Any = Column(Integer, nullable=False, default=0)
    rotation_type: Any = Column(String(20), nullable=False)
    last_rotated_at: Any = Column(DateTime, nullable=True)
    created_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class EscalationPolicy(Base):
    """Database model representing an escalation policy for unresolved incidents."""

    __tablename__ = "escalation_policies"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Any = Column(String(255), nullable=False)
    severity: Any = Column(String(20), nullable=False, unique=True)
    timeout_minutes: Any = Column(Integer, nullable=False)
    target_type: Any = Column(String(20), nullable=False)
    target_identifier: Any = Column(String(255), nullable=False)
    created_at: Any = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SystemSettings(Base):
    """Database model representing global system settings key-value pairs."""

    __tablename__ = "system_settings"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Any = Column(String(255), nullable=False, unique=True, index=True)
    value: Any = Column(Text, nullable=True)
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
