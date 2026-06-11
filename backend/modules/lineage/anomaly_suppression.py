import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge
from backend.modules.anomaly.models import AnomalyDetection

logger = logging.getLogger("qolyx.lineage.anomaly_suppression")

COOLDOWN_PERIOD_HOURS = 2


def get_downstream_nodes(db: Session, node_id: str) -> List[str]:
    """Recursively queries all downstream target node IDs starting from the given source node_id."""
    logger.info("Fetching downstream nodes recursively", extra={"node_id": node_id})
    try:
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
        rows = db.execute(query, {"node_id": node_id}).fetchall()
        return [str(row[0]) for row in rows]
    except Exception as e:
        logger.error(f"Failed recursive downstream query for node {node_id}", exc_info=True)
        return []


def suppress_anomaly_for_lineage(db: Session, source_node_id: str, anomaly_id: uuid.UUID) -> None:
    """Finds all downstream nodes of the source node and marks their recent anomalies as suppressed.

    Sets suppressed_by_lineage = True and root_cause_anomaly_id = anomaly_id.
    """
    logger.info(
        "Suppressing downstream anomalies based on source anomaly",
        extra={"source_node_id": source_node_id, "anomaly_id": str(anomaly_id)}
    )

    try:
        # 1. Fetch downstream nodes
        downstream_ids = get_downstream_nodes(db, source_node_id)
        if not downstream_ids:
            return

        # 2. Map node IDs to table names
        table_names = {nid.split(".")[-1] for nid in downstream_ids}
        logger.info(f"Targeting downstream tables for suppression: {table_names}")

        # 3. Find recent anomalies for downstream tables within the cooldown period
        cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_PERIOD_HOURS)
        recent_anomalies = db.query(AnomalyDetection).filter(
            AnomalyDetection.table_name.in_(table_names),
            AnomalyDetection.created_at >= cooldown_time,
            AnomalyDetection.suppressed_by_lineage == False
        ).all()

        # 4. Mark them as suppressed
        for anomaly in recent_anomalies:
            # Do not suppress the root cause anomaly itself
            if anomaly.id == anomaly_id:
                continue

            anomaly.suppressed_by_lineage = True
            anomaly.root_cause_anomaly_id = anomaly_id
            anomaly.updated_at = datetime.now(timezone.utc)
            logger.info(
                f"Suppressed downstream anomaly",
                extra={
                    "anomaly_id": str(anomaly.id),
                    "table_name": anomaly.table_name,
                    "root_cause_id": str(anomaly_id)
                }
            )

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to suppress downstream anomalies for root cause {anomaly_id}",
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
        # 1. Look up the lineage node for this table
        node = db.query(LineageNode).filter(LineageNode.node_id == detection.table_name).first()
        if not node:
            node = db.query(LineageNode).filter(LineageNode.node_id.like(f"%.{detection.table_name}")).first()
        
        if not node:
            return

        # 2. Query all active upstream ancestors recursively
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
        rows = db.execute(query, {"node_id": node.node_id}).fetchall()
        ancestor_ids = [str(row[0]) for row in rows]
        if not ancestor_ids:
            return

        # 3. Extract table names from ancestor node IDs
        ancestor_tables = {nid.split(".")[-1] for nid in ancestor_ids}

        # 4. Check for active root-cause anomalies in ancestors within the cooldown window
        cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_PERIOD_HOURS)
        upstream_anomaly = db.query(AnomalyDetection).filter(
            AnomalyDetection.table_name.in_(ancestor_tables),
            AnomalyDetection.created_at >= cooldown_time,
            AnomalyDetection.suppressed_by_lineage == False
        ).order_by(AnomalyDetection.created_at.desc()).first()

        if upstream_anomaly:
            # Mark the new anomaly as suppressed
            detection.suppressed_by_lineage = True
            detection.root_cause_anomaly_id = upstream_anomaly.id
            # Disable immediate alerting by clearing last_alerted_at
            detection.last_alerted_at = None
            logger.info(
                f"Lineage Suppression: Suppressed anomaly on '{detection.table_name}' due to upstream anomaly on '{upstream_anomaly.table_name}'",
                extra={
                    "anomaly_id": str(detection.id),
                    "upstream_table": upstream_anomaly.table_name,
                    "root_cause_id": str(upstream_anomaly.id)
                }
            )
    except Exception as e:
        logger.error(
            f"Failed to run lineage-driven anomaly suppression check for table {detection.table_name}",
            exc_info=True
        )

