import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from backend.core.database import Base

class BronzeFinancialCandle(Base):
    """Bronze financial candle data ingested from Finnhub."""
    __tablename__ = "bronze_financial_candles"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, index=True)
    symbol: Any = Column(String, nullable=False, index=True)
    open_price: Any = Column(Float, nullable=True)
    high_price: Any = Column(Float, nullable=True)
    low_price: Any = Column(Float, nullable=True)
    close_price: Any = Column(Float, nullable=True)
    volume: Any = Column(Integer, nullable=True)
    candle_timestamp: Any = Column(DateTime, nullable=False)
    ingested_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class BronzeFdaEvent(Base):
    """Bronze FDA Drug Adverse Events data."""
    __tablename__ = "bronze_fda_events"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, index=True)
    receipt_date: Any = Column(String, nullable=True)
    serious: Any = Column(String, nullable=True)
    reporter_country: Any = Column(String, nullable=True)
    drug_name: Any = Column(String, nullable=True)
    reaction_description: Any = Column(String, nullable=True)
    seriousness_hospitalization: Any = Column(String, nullable=True)
    raw_payload: Any = Column(JSON, nullable=False)
    ingested_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class BronzeGithubEvent(Base):
    """Bronze GitHub Archive events data."""
    __tablename__ = "bronze_github_events"

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_id: Any = Column(String, nullable=False, unique=True)
    event_type: Any = Column(String, nullable=False, index=True)
    actor_login: Any = Column(String, nullable=True)
    repo_name: Any = Column(String, nullable=True)
    payload_action: Any = Column(String, nullable=True)
    created_at: Any = Column(DateTime, nullable=True)
    raw_payload: Any = Column(JSON, nullable=False)
    ingested_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
