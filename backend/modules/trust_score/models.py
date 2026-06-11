import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from backend.core.database import Base


class TrustScore(Base):
    """Database model for storing ingestion pipeline run trust scores and penalty breakdowns."""
    __tablename__ = "trust_scores"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Any = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    table_name: Any = Column(String(255), nullable=False, index=True)
    contract_penalty: Any = Column(Integer, nullable=False, default=0)
    freshness_penalty: Any = Column(Integer, nullable=False, default=0)
    volume_penalty: Any = Column(Integer, nullable=False, default=0)
    anomaly_penalty: Any = Column(Integer, nullable=False, default=0)
    dbt_penalty: Any = Column(Integer, nullable=False, default=0)
    total_penalty: Any = Column(Integer, nullable=False)
    trust_score: Any = Column(Integer, nullable=False)
    trust_score_status: Any = Column(String(50), nullable=False)
    created_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Any = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def breakdown(self) -> dict[str, int]:
        """Penalty breakdown dictionary for easy JSON API serialization."""
        from sqlalchemy.orm import object_session
        from backend.modules.lineage.models import LineageNode

        lineage_pen = 0
        session = object_session(self)
        if session:
            # Look up lineage node representing this table
            node = session.query(LineageNode).filter(
                LineageNode.node_id == self.table_name
            ).first()
            if not node:
                # Fallback check for dbt style node_id: model.project.table_name
                node = session.query(LineageNode).filter(
                    LineageNode.node_id.like(f"%.{self.table_name}")
                ).first()
            if node and node.meta:
                lineage_pen = int(node.meta.get("lineage_penalty", 0))

        return {
            "contract_penalty": self.contract_penalty or 0,
            "freshness_penalty": self.freshness_penalty or 0,
            "volume_penalty": self.volume_penalty or 0,
            "anomaly_penalty": self.anomaly_penalty or 0,
            "dbt_penalty": self.dbt_penalty or 0,
            "lineage_penalty": lineage_pen,
        }

