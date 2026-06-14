import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge, LineageColumnEdge
from backend.modules.anomaly.models import AnomalyDetection

logger = logging.getLogger("qolyx.lineage.anomaly_suppression")

COOLDOWN_PERIOD_HOURS = 2


def resolve_full_node_id(db: Session, node_id: str) -> str:
    """Resolves a short table name or partial node_id to the full node_id in the graph."""
    if "." in node_id:
        return node_id
    node = db.query(LineageNode).filter(
        (LineageNode.node_id == node_id) |
        (LineageNode.node_id.like(f"%.{node_id}"))
    ).first()
    return node.node_id if node else node_id


def get_anomaly_column(anomaly: AnomalyDetection) -> Optional[str]:
    """Helper to extract the specific column name from an anomaly if it's column-level."""
    if not anomaly:
        return None
    # 1. Check if column_name attribute exists on anomaly
    if hasattr(anomaly, "column_name") and getattr(anomaly, "column_name"):
        return getattr(anomaly, "column_name")
        
    # 2. Check feature_values feature_importance for primary null_rate_ feature
    if anomaly.feature_values and "feature_importance" in anomaly.feature_values:
        importance = anomaly.feature_values["feature_importance"]
        if importance:
            primary = max(importance.keys(), key=lambda k: abs(importance[k]))
            if primary.startswith("null_rate_"):
                return primary[len("null_rate_"):]
                
    # 3. Check anomaly_type prefix/suffix
    if anomaly.anomaly_type and "null_rate_" in anomaly.anomaly_type:
        return anomaly.anomaly_type.replace("null_rate_", "")
        
    return None


def get_downstream_nodes(db: Session, node_id: str) -> List[str]:
    """Recursively queries all downstream target node IDs starting from the given source node_id."""
    logger.info("Fetching downstream nodes recursively", extra={"node_id": node_id})
    try:
        resolved_id = resolve_full_node_id(db, node_id)
        query = text("""
            WITH RECURSIVE downstream_nodes AS (
                SELECT target_node_id
                FROM lineage_edges
                WHERE source_node_id = :node_id AND valid_to IS NULL
                UNION
                SELECT e.target_node_id
                FROM lineage_edges e
                INNER JOIN downstream_nodes d ON e.source_node_id = d.target_node_id
                WHERE e.valid_to IS NULL
            )
            SELECT DISTINCT target_node_id FROM downstream_nodes;
        """)
        rows = db.execute(query, {"node_id": resolved_id}).fetchall()
        return [str(row[0]) for row in rows]
    except Exception as e:
        logger.error(f"Failed recursive downstream query for node {node_id}", exc_info=True)
        return []


def get_downstream_columns(db: Session, node_id: str, column_name: str) -> List[tuple]:
    """Recursively queries all downstream target column paths starting from the given source (node_id, column_name)."""
    logger.info("Fetching downstream columns recursively", extra={"node_id": node_id, "column_name": column_name})
    try:
        resolved_id = resolve_full_node_id(db, node_id)
        query = text("""
            WITH RECURSIVE downstream_cols AS (
                SELECT target_node_id, target_column
                FROM lineage_column_edges
                WHERE source_node_id = :node_id AND source_column = :column_name AND valid_to IS NULL
                UNION
                SELECT e.target_node_id, e.target_column
                FROM lineage_column_edges e
                INNER JOIN downstream_cols d ON e.source_node_id = d.target_node_id AND e.source_column = d.target_column
                WHERE e.valid_to IS NULL
            )
            SELECT DISTINCT target_node_id, target_column FROM downstream_cols;
        """)
        rows = db.execute(query, {"node_id": resolved_id, "column_name": column_name}).fetchall()
        return [(str(row[0]), str(row[1])) for row in rows]
    except Exception as e:
        logger.error(f"Failed recursive downstream query for column {node_id}.{column_name}", exc_info=True)
        return []


def get_upstream_columns(db: Session, node_id: str, column_name: str) -> List[tuple]:
    """Recursively queries all upstream source columns starting from the given target (node_id, column_name)."""
    try:
        resolved_id = resolve_full_node_id(db, node_id)
        query = text("""
            WITH RECURSIVE upstream_cols AS (
                SELECT source_node_id, source_column
                FROM lineage_column_edges
                WHERE target_node_id = :node_id AND target_column = :column_name AND valid_to IS NULL
                UNION
                SELECT e.source_node_id, e.source_column
                FROM lineage_column_edges e
                INNER JOIN upstream_cols u ON e.target_node_id = u.source_node_id AND e.target_column = u.source_column
                WHERE e.valid_to IS NULL
            )
            SELECT DISTINCT source_node_id, source_column FROM upstream_cols;
        """)
        rows = db.execute(query, {"node_id": resolved_id, "column_name": column_name}).fetchall()
        return [(str(row[0]), str(row[1])) for row in rows]
    except Exception as e:
        logger.error(f"Failed recursive upstream query for column {node_id}.{column_name}", exc_info=True)
        return []


def suppress_anomaly_for_lineage(db: Session, source_node_id: str, anomaly_id: uuid.UUID) -> None:
    """Finds all downstream nodes/columns of the source node and marks their recent anomalies as suppressed.

    Sets suppressed_by_lineage = True and root_cause_anomaly_id = anomaly_id.
    Supports column-level precision.
    """
    logger.info(
        "Suppressing downstream anomalies based on source anomaly",
        extra={"source_node_id": source_node_id, "anomaly_id": str(anomaly_id)}
    )

    try:
        # Find the source anomaly
        anomaly = db.query(AnomalyDetection).filter(AnomalyDetection.id == anomaly_id).first()
        if not anomaly:
            logger.warning(f"Source anomaly {anomaly_id} not found; skipping suppression.")
            return

        resolved_src_id = resolve_full_node_id(db, source_node_id)
        src_col = get_anomaly_column(anomaly)
        cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_PERIOD_HOURS)

        if src_col:
            # Column-level suppression
            downstream_cols = get_downstream_columns(db, resolved_src_id, src_col)
            if not downstream_cols:
                logger.info("No downstream column lineage paths found for column-level suppression.")
                return

            for target_node_id, target_col in downstream_cols:
                target_table = target_node_id.split(".")[-1]
                recent_anomalies = db.query(AnomalyDetection).filter(
                    AnomalyDetection.table_name == target_table,
                    AnomalyDetection.created_at >= cooldown_time,
                    AnomalyDetection.suppressed_by_lineage == False
                ).all()

                for child_anomaly in recent_anomalies:
                    if child_anomaly.id == anomaly_id:
                        continue
                    child_col = get_anomaly_column(child_anomaly)
                    if child_col == target_col:
                        child_anomaly.suppressed_by_lineage = True
                        child_anomaly.root_cause_anomaly_id = anomaly_id
                        child_anomaly.updated_at = datetime.now(timezone.utc)
                        logger.info(
                            "Suppressed downstream column-level anomaly",
                            extra={
                                "anomaly_id": str(child_anomaly.id),
                                "table_name": child_anomaly.table_name,
                                "column_name": child_col,
                                "root_cause_id": str(anomaly_id)
                            }
                        )
        else:
            # Table-level suppression (existing fallback)
            downstream_ids = get_downstream_nodes(db, resolved_src_id)
            if not downstream_ids:
                return

            table_names = {nid.split(".")[-1] for nid in downstream_ids}
            recent_anomalies = db.query(AnomalyDetection).filter(
                AnomalyDetection.table_name.in_(table_names),
                AnomalyDetection.created_at >= cooldown_time,
                AnomalyDetection.suppressed_by_lineage == False
            ).all()

            for child_anomaly in recent_anomalies:
                if child_anomaly.id == anomaly_id:
                    continue

                child_anomaly.suppressed_by_lineage = True
                child_anomaly.root_cause_anomaly_id = anomaly_id
                child_anomaly.updated_at = datetime.now(timezone.utc)
                logger.info(
                    "Suppressed downstream table-level anomaly",
                    extra={
                        "anomaly_id": str(child_anomaly.id),
                        "table_name": child_anomaly.table_name,
                        "root_cause_id": str(anomaly_id)
                    }
                )

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to suppress downstream anomalies for root cause {anomaly_id}: {e}",
            exc_info=True
        )
        raise


def get_root_cause_anomalies(db: Session, anomaly_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Recursively traces up the suppression chain to find the original root cause anomaly."""
    try:
        anomaly = db.query(AnomalyDetection).filter(AnomalyDetection.id == anomaly_id).first()
        if not anomaly:
            return None

        # If it is suppressed by another anomaly, recurse
        if anomaly.suppressed_by_lineage and anomaly.root_cause_anomaly_id:
            return get_root_cause_anomalies(db, anomaly.root_cause_anomaly_id)

        # Return root cause representation
        return {
            "id": str(anomaly.id),
            "pipeline_run_id": str(anomaly.pipeline_run_id),
            "table_name": anomaly.table_name,
            "column_name": get_anomaly_column(anomaly),
            "anomaly_type": anomaly.anomaly_type,
            "anomaly_score": anomaly.anomaly_score,
            "explanation": anomaly.explanation,
            "created_at": anomaly.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trace root cause for anomaly {anomaly_id}", exc_info=True)
        return None


def group_alerts_by_root_cause(db: Session, anomaly_ids: List[uuid.UUID]) -> Dict[str, List[Dict[str, Any]]]:
    """Groups a list of anomalies by their root cause anomaly.

    Returns:
        Dict mapping root_cause_anomaly_id (as str) to list of anomaly dict representations.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for aid in anomaly_ids:
            anomaly = db.query(AnomalyDetection).filter(AnomalyDetection.id == aid).first()
            if not anomaly:
                continue

            root_cause = get_root_cause_anomalies(db, aid)
            root_id = root_cause["id"] if root_cause else str(aid)

            anomaly_dict = {
                "id": str(anomaly.id),
                "table_name": anomaly.table_name,
                "column_name": get_anomaly_column(anomaly),
                "anomaly_type": anomaly.anomaly_type,
                "anomaly_score": anomaly.anomaly_score,
                "suppressed": anomaly.suppressed_by_lineage,
                "root_cause_id": root_id,
                "created_at": anomaly.created_at.isoformat()
            }

            if root_id not in groups:
                groups[root_id] = []
            groups[root_id].append(anomaly_dict)
    except Exception as e:
        logger.error("Failed to group anomalies by root cause", exc_info=True)
    return groups


def check_and_suppress_new_anomaly(db: Session, detection: AnomalyDetection) -> None:
    """Checks if a newly detected anomaly should be suppressed because of an existing upstream anomaly."""
    try:
        resolved_id = resolve_full_node_id(db, detection.table_name)
        detection_col = get_anomaly_column(detection)
        cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_PERIOD_HOURS)

        # Helper to check table-level upstream anomalies
        def check_table_level_upstream() -> Optional[AnomalyDetection]:
            query = text("""
                WITH RECURSIVE upstream_nodes AS (
                    SELECT source_node_id
                    FROM lineage_edges
                    WHERE target_node_id = :node_id AND valid_to IS NULL
                    UNION
                    SELECT e.source_node_id
                    FROM lineage_edges e
                    INNER JOIN upstream_nodes u ON e.target_node_id = u.source_node_id
                    WHERE e.valid_to IS NULL
                )
                SELECT DISTINCT source_node_id FROM upstream_nodes;
            """)
            rows = db.execute(query, {"node_id": resolved_id}).fetchall()
            ancestor_ids = [str(row[0]) for row in rows]
            if not ancestor_ids:
                return None
            ancestor_tables = {nid.split(".")[-1] for nid in ancestor_ids}

            # Find active table-level anomalies in upstream tables
            upstream_anomaly = db.query(AnomalyDetection).filter(
                AnomalyDetection.table_name.in_(ancestor_tables),
                AnomalyDetection.created_at >= cooldown_time,
                AnomalyDetection.suppressed_by_lineage == False
            ).order_by(AnomalyDetection.created_at.desc()).first()
            
            # Ensure it is a table-level anomaly (column_name is None) or just any active upstream anomaly
            # A full table anomaly suppresses any downstream column anomalies.
            return upstream_anomaly

        # 1. If it's a column-level anomaly, check column-level upstream paths
        if detection_col:
            upstream_cols = get_upstream_columns(db, resolved_id, detection_col)
            for parent_node_id, parent_col in upstream_cols:
                parent_table = parent_node_id.split(".")[-1]
                # Check for active anomaly on parent_table for parent_col
                upstream_col_anomaly = db.query(AnomalyDetection).filter(
                    AnomalyDetection.table_name == parent_table,
                    AnomalyDetection.created_at >= cooldown_time,
                    AnomalyDetection.suppressed_by_lineage == False
                ).all()

                for uca in upstream_col_anomaly:
                    if get_anomaly_column(uca) == parent_col:
                        detection.suppressed_by_lineage = True
                        detection.root_cause_anomaly_id = uca.id
                        detection.last_alerted_at = None
                        logger.info(
                            f"Lineage Suppression: Suppressed column-level anomaly on '{detection.table_name}.{detection_col}' due to upstream column anomaly on '{parent_table}.{parent_col}'",
                            extra={
                                "anomaly_id": str(detection.id),
                                "upstream_table": parent_table,
                                "upstream_column": parent_col,
                                "root_cause_id": str(uca.id)
                            }
                        )
                        return

        # 2. Check table-level upstream anomalies (fallback for column-level, or primary check for table-level)
        upstream_table_anomaly = check_table_level_upstream()
        if upstream_table_anomaly:
            detection.suppressed_by_lineage = True
            detection.root_cause_anomaly_id = upstream_table_anomaly.id
            detection.last_alerted_at = None
            logger.info(
                f"Lineage Suppression: Suppressed anomaly on '{detection.table_name}' due to upstream table anomaly on '{upstream_table_anomaly.table_name}'",
                extra={
                    "anomaly_id": str(detection.id),
                    "upstream_table": upstream_table_anomaly.table_name,
                    "root_cause_id": str(upstream_table_anomaly.id)
                }
            )
            return

    except Exception as e:
        logger.error(
            f"Failed to run lineage-driven anomaly suppression check for table {detection.table_name}: {e}",
            exc_info=True
        )

