import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    JSON,
    ForeignKey,
    Float,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.core.database import Base


class LineageNode(Base):
    """Database model representing a node in the data lineage graph.

    A node can be a dbt model, warehouse table, source, test, seed, or exposure.
    """
    __tablename__ = "lineage_nodes"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Any = Column(String(255), unique=True, nullable=False, index=True)
    name: Any = Column(String(255), nullable=False)
    type: Any = Column(String(50), nullable=False)  # source, model, seed, test, exposure, warehouse_table
    schema: Any = Column(String(255), nullable=False)
    database: Any = Column(String(255), nullable=True)
    materialized_type: Any = Column(String(50), nullable=True)
    owner: Any = Column(String(255), nullable=True)
    description: Any = Column(Text, nullable=True)
    meta: Any = Column(JSON, nullable=True)
    trust_score: Any = Column(Float, nullable=True)
    last_updated_at: Any = Column(DateTime, nullable=True)
    created_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the lineage node to a dictionary representation."""
        return {
            "id": str(self.id),
            "node_id": self.node_id,
            "name": self.name,
            "type": self.type,
            "schema": self.schema,
            "database": self.database,
            "materialized_type": self.materialized_type,
            "owner": self.owner,
            "description": self.description,
            "meta": self.meta,
            "trust_score": self.trust_score,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LineageEdge(Base):
    """Database model representing an active dependency edge between two LineageNodes."""
    __tablename__ = "lineage_edges"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id: Any = Column(
        String(255),
        ForeignKey("lineage_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_node_id: Any = Column(
        String(255),
        ForeignKey("lineage_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    edge_type: Any = Column(String(50), nullable=False)  # depends_on, references, parent_of
    valid_from: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    valid_to: Any = Column(DateTime, nullable=True)  # NULL = currently active
    created_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships for traversal
    source_node = relationship(
        "LineageNode",
        foreign_keys=[source_node_id],
        backref="downstream_edges"
    )
    target_node = relationship(
        "LineageNode",
        foreign_keys=[target_node_id],
        backref="upstream_edges"
    )

    __table_args__ = (
        Index("idx_lineage_edges_source_target", "source_node_id", "target_node_id"),
        Index("idx_lineage_edges_valid_from_to", "valid_from", "valid_to"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the lineage edge to a dictionary representation."""
        return {
            "id": str(self.id),
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LineageEdgeHistory(Base):
    """Database model representing a historic/recorded dependency edge for temporal queries.

    Tracks lineage state over time.
    """
    __tablename__ = "lineage_edge_history"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id: Any = Column(String(255), nullable=False, index=True)
    target_node_id: Any = Column(String(255), nullable=False, index=True)
    edge_type: Any = Column(String(50), nullable=False)
    valid_from: Any = Column(DateTime, nullable=False)
    valid_to: Any = Column(DateTime, nullable=True)
    recorded_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_lineage_history_source_target", "source_node_id", "target_node_id"),
        Index("idx_lineage_history_valid_from_to", "valid_from", "valid_to"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the lineage edge history record to a dictionary representation."""
        return {
            "id": str(self.id),
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class LineageColumnEdge(Base):
    """Database model representing an active dependency edge between two columns."""
    __tablename__ = "lineage_column_edges"
    __allow_unmapped__ = True

    id: Any = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id: Any = Column(
        String(255),
        ForeignKey("lineage_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_column: Any = Column(String(255), nullable=False)
    target_node_id: Any = Column(
        String(255),
        ForeignKey("lineage_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_column: Any = Column(String(255), nullable=False)
    edge_type: Any = Column(String(50), nullable=False, default="direct")  # direct, derived, aggregate
    valid_from: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    valid_to: Any = Column(DateTime, nullable=True)  # NULL = currently active
    transformation_rule: Any = Column(Text, nullable=True)
    created_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Any = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships for traversal
    source_node = relationship(
        "LineageNode",
        foreign_keys=[source_node_id],
        backref="downstream_column_edges"
    )
    target_node = relationship(
        "LineageNode",
        foreign_keys=[target_node_id],
        backref="upstream_column_edges"
    )

    __table_args__ = (
        Index("idx_col_edges_source", "source_node_id", "source_column"),
        Index("idx_col_edges_target", "target_node_id", "target_column"),
        Index("idx_col_edges_valid_from_to", "valid_from", "valid_to"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the lineage column edge to a dictionary representation."""
        return {
            "id": str(self.id),
            "source_node_id": self.source_node_id,
            "source_column": self.source_column,
            "target_node_id": self.target_node_id,
            "target_column": self.target_column,
            "edge_type": self.edge_type,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "transformation_rule": self.transformation_rule,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

