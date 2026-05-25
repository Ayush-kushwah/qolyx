import uuid
from datetime import datetime, timezone
from typing import Any, List
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Boolean, ForeignKey, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base

class AnomalyBaseline(Base):
    """SQLAlchemy model representing the baseline distribution statistics for feature metrics."""
    __tablename__ = "anomaly_baselines"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name: Any = Column(String(255), nullable=False, index=True)
    metric_name: Any = Column(String(255), nullable=False)
    feature_columns: Any = Column(JSON, nullable=False)
    mean: Any = Column(Float, nullable=False)
    std_dev: Any = Column(Float, nullable=False)
    model_name: Any = Column(String(100), nullable=True)
    feature_importance: Any = Column(JSON, nullable=True)
    isolation_forest_params: Any = Column(JSON, nullable=True)
    training_run_count: Any = Column(Integer, nullable=False, default=0)
    last_trained_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    decay_factor: Any = Column(Float, nullable=False, default=0.95)
    created_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AnomalyDetection(Base):
    """SQLAlchemy model representing a single detected data quality anomaly."""
    __tablename__ = "anomaly_detections"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, index=True)
    table_name: Any = Column(String(255), nullable=False, index=True)
    anomaly_type: Any = Column(String(50), nullable=False)
    anomaly_score: Any = Column(Float, nullable=False)
    anomaly_penalty: Any = Column(Integer, nullable=False)
    feature_values: Any = Column(JSON, nullable=True)
    explanation: Any = Column(Text, nullable=True)
    is_acknowledged: Any = Column(Boolean, nullable=False, default=False)
    is_false_positive: Any = Column(Boolean, nullable=False, default=False)
    last_alerted_at: Any = Column(DateTime, nullable=True)
    created_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    feedback: Any = relationship("AnomalyFeedback", back_populates="detection", cascade="all, delete-orphan")


class AnomalyFeedback(Base):
    """SQLAlchemy model representing user feedback submitted for a detected anomaly."""
    __tablename__ = "anomaly_feedback"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anomaly_detection_id: Any = Column(UUID(as_uuid=True), ForeignKey("anomaly_detections.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type: Any = Column(String(20), nullable=False)
    user_notes: Any = Column(Text, nullable=True)
    created_by: Any = Column(String(255), nullable=False)
    created_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    detection: Any = relationship("AnomalyDetection", back_populates="feedback")


class SilverAnomalyFeature(Base):
    """SQLAlchemy model mapped to the silver_anomaly_features dbt table (Read-Only)."""
    __tablename__ = "silver_anomaly_features"
    __allow_unmapped__ = True
    __table_args__ = {"schema": "public_silver"}

    pipeline_run_id: Any = Column(UUID(as_uuid=True), primary_key=True)
    source_name: Any = Column(String(255), nullable=False)
    row_count: Any = Column(Integer, nullable=False)
    null_rates: Any = Column(JSON, nullable=False)
    mean_close_price: Any = Column(Float, nullable=True)
    total_volume: Any = Column(BigInteger, nullable=True)
    unique_events_count: Any = Column(Integer, nullable=True)
    freshness_latency_seconds: Any = Column(Float, nullable=True)
    run_timestamp: Any = Column(DateTime, nullable=False)
