import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Integer, JSON, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base

class Contract(Base):
    """Database model for data contracts defining expected schema definitions."""
    __tablename__ = "contracts"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Any = Column(String(255), unique=True, nullable=False)
    table_name: Any = Column(String(255), nullable=False)
    version: Any = Column(Integer, nullable=False, default=1)
    schema_definition: Any = Column(JSON, nullable=False)
    is_active: Any = Column(Boolean, nullable=False, default=True)
    created_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to violations
    violations: Any = relationship("ContractViolation", back_populates="contract", cascade="all, delete-orphan")


class ContractViolation(Base):
    """Database model for storing individual contract violations discovered during ingestion."""
    __tablename__ = "contract_violations"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Any = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, index=True)
    violation_type: Any = Column(String(50), nullable=False)  # missing_column, wrong_type, null_violation, extra_column
    column_name: Any = Column(String(255), nullable=True)
    expected_value: Any = Column(String(255), nullable=True)
    actual_value: Any = Column(String(255), nullable=True)
    penalty_amount: Any = Column(Integer, nullable=False, default=0)
    description: Any = Column(Text, nullable=False)
    created_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship to contract
    contract: Any = relationship("Contract", back_populates="violations")
