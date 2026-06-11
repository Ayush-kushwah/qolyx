import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from sqlalchemy.orm import Session

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge
from backend.modules.trust_score.models import TrustScore

logger = logging.getLogger("qolyx.lineage.health")

DECAY_FACTOR = 0.9
MAX_PENALTY_LIMIT = 40.0


def propagate_health_score(db: Session, source_node_id: str, new_score: float) -> None:
    """Propagates trust score changes from a source node to all downstream nodes recursively.

    Applies a decay factor of 0.9 per hop, capping the propagated lineage penalty at 40.0.
    """
    logger.info(
        "Initiating health score propagation",
        extra={"source_node_id": source_node_id, "new_score": new_score}
    )

    try:
        # 1. Update source node trust score
        source_node = db.query(LineageNode).filter(LineageNode.node_id == source_node_id).first()
        if not source_node:
            logger.warning(
                f"Source node not found in lineage graph; cannot propagate",
                extra={"source_node_id": source_node_id}
            )
            return

        source_node.trust_score = float(new_score)
        source_node.last_updated_at = datetime.now(timezone.utc)
        db.flush()

        # 2. BFS traversal downstream
        queue: List[str] = [source_node_id]
        visited: Set[str] = {source_node_id}

        while queue:
            current_id = queue.pop(0)

            # Find active downstream edges
            edges = db.query(LineageEdge).filter(
                LineageEdge.source_node_id == current_id,
                LineageEdge.valid_to == None
            ).all()

            for edge in edges:
                child_id = edge.target_node_id
                if child_id in visited:
                    continue
                visited.add(child_id)

                child_node = db.query(LineageNode).filter(LineageNode.node_id == child_id).first()
                if not child_node:
                    continue

                # Calculate child health based on all its parents
                parents_edges = db.query(LineageEdge).filter(
                    LineageEdge.target_node_id == child_id,
                    LineageEdge.valid_to == None
                ).all()

                max_propagated_penalty = 0.0
                for pe in parents_edges:
                    parent = db.query(LineageNode).filter(LineageNode.node_id == pe.source_node_id).first()
                    if parent and parent.trust_score is not None:
                        parent_penalty = 100.0 - parent.trust_score
                        propagated = parent_penalty * DECAY_FACTOR
                        if propagated > max_propagated_penalty:
                            max_propagated_penalty = propagated

                # Cap the propagated penalty
                lineage_penalty = min(max_propagated_penalty, MAX_PENALTY_LIMIT)

                # Fetch child's own independent base score from trust_scores table
                table_name = child_id.split(".")[-1]
                latest_ts = db.query(TrustScore).filter(
                    TrustScore.table_name == table_name
                ).order_by(TrustScore.created_at.desc()).first()

                if latest_ts:
                    # Base score is the score before lineage penalty propagation
                    # If the latest trust score doesn't exclude lineage penalty (which is calculated here),
                    # its base score is calculated from its own penalties.
                    base_score = float(100 - (
                        latest_ts.contract_penalty +
                        latest_ts.freshness_penalty +
                        latest_ts.volume_penalty +
                        latest_ts.anomaly_penalty +
                        latest_ts.dbt_penalty
                    ))
                else:
                    base_score = 100.0

                # Calculate final score and store in child node
                final_score = max(0.0, base_score - lineage_penalty)
                child_node.trust_score = final_score
                child_node.last_updated_at = datetime.now(timezone.utc)

                # Store lineage_penalty in node meta for transparency
                if not child_node.meta:
                    child_node.meta = {}
                child_node.meta["lineage_penalty"] = lineage_penalty
                child_node.meta["base_score"] = base_score

                # Queue child for downstream propagation
                queue.append(child_id)

        db.commit()
        logger.info("Health score propagation completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to propagate health score for {source_node_id}",
            exc_info=True,
            extra={"source_node_id": source_node_id}
        )
        raise


def get_critical_path(db: Session, node_id: str) -> List[Dict[str, Any]]:
    """Traces the path of upstream dependencies that has the highest negative health impact on the given node."""
    path: List[Dict[str, Any]] = []

    def trace_upstream(current_id: str) -> List[str]:
        edges = db.query(LineageEdge).filter(
            LineageEdge.target_node_id == current_id,
            LineageEdge.valid_to == None
        ).all()

        if not edges:
            return [current_id]

        worst_parent_path: List[str] = []
        max_effective_penalty = -1.0

        for edge in edges:
            parent_id = edge.source_node_id
            parent_node = db.query(LineageNode).filter(LineageNode.node_id == parent_id).first()
            if parent_node:
                parent_penalty = 100.0 - (parent_node.trust_score or 100.0)
                parent_path = trace_upstream(parent_id)
                # Effective penalty decays by decay factor per hop
                effective_penalty = parent_penalty * (DECAY_FACTOR ** (len(parent_path) - 1))

                if effective_penalty > max_effective_penalty:
                    max_effective_penalty = effective_penalty
                    worst_parent_path = parent_path

        if not worst_parent_path:
            return [current_id]

        return worst_parent_path + [current_id]

    try:
        node_ids = trace_upstream(node_id)
        for nid in node_ids:
            node = db.query(LineageNode).filter(LineageNode.node_id == nid).first()
            if node:
                path.append(node.to_dict())
    except Exception as e:
        logger.error(f"Failed to trace critical path for {node_id}", exc_info=True)

    return path


def schedule_propagation(db: Session) -> None:
    """Finds all root sources (nodes with no active upstream edges) and runs health score propagation downstream.

    Typically run as a background job or after any trust score update.
    """
    logger.info("Executing scheduled health score propagation across lineage graph...")
    try:
        # Find all nodes
        all_nodes = db.query(LineageNode).all()
        for node in all_nodes:
            # Check if it has any upstream edges
            upstream_count = db.query(LineageEdge).filter(
                LineageEdge.target_node_id == node.node_id,
                LineageEdge.valid_to == None
            ).count()

            if upstream_count == 0:
                # Root source node, initiate propagation from here
                propagate_health_score(db, node.node_id, node.trust_score or 100.0)
    except Exception as e:
        logger.error("Failed to execute scheduled health score propagation", exc_info=True)
