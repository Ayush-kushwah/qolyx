import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import func

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge, LineageColumnEdge
from backend.modules.trust_score.models import TrustScore

logger = logging.getLogger("qolyx.lineage.health")

DECAY_FACTOR = 0.9
MAX_PENALTY_LIMIT = 40.0


def propagate_health_score(db: Session, source_node_id: str, new_score: float) -> None:
    """Propagates trust score changes from a source node to all downstream nodes recursively.

    Applies a decay factor of 0.9 per hop, limiting trust score decay propagation
    only to downstream nodes/columns that depend on the specific failed columns.
    """
    logger.info(
        "Initiating column-level health score propagation",
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

        # In-memory mapping to track column-level and table-level penalties for each traversed node
        # node_penalties[node_id] = {"cols": {col_name: penalty_val}, "table_only_penalty": val}
        node_penalties = {}

        # Initialize the source node's penalties
        src_table_name = source_node_id.split(".")[-1]
        
        from backend.modules.contracts.models import ContractViolation
        from backend.modules.anomaly.models import AnomalyDetection
        
        col_penalties = {}
        table_only_penalty = 0.0

        # Query base score from the latest TrustScore run
        latest_ts = db.query(TrustScore).filter(
            TrustScore.table_name == src_table_name
        ).order_by(TrustScore.created_at.desc()).first()

        if latest_ts:
            # Table-only penalties (freshness, volume, dbt)
            table_only_penalty = float(
                latest_ts.freshness_penalty +
                latest_ts.volume_penalty +
                latest_ts.dbt_penalty
            )
            
            # Map contract violations to columns
            from backend.modules.contracts.models import Contract
            violations = db.query(ContractViolation).join(Contract).filter(
                Contract.table_name == src_table_name
            ).all()
            for v in violations:
                if v.column_name:
                    col_penalties[v.column_name] = col_penalties.get(v.column_name, 0.0) + v.penalty_amount
                else:
                    table_only_penalty += v.penalty_amount

            # Map anomalies to columns
            anomalies = db.query(AnomalyDetection).filter(
                AnomalyDetection.table_name == src_table_name,
                AnomalyDetection.is_false_positive == False
            ).all()
            for a in anomalies:
                col_name = getattr(a, "column_name", None) or a.metric_name
                cols_list = source_node.meta.get("columns", {}) if source_node.meta else {}
                if not col_name and a.metric_name in cols_list:
                    col_name = a.metric_name
                
                penalty = int(getattr(a, "anomaly_penalty", 0)) or int((a.anomaly_score or 0) * 20)
                if col_name:
                    col_penalties[col_name] = col_penalties.get(col_name, 0.0) + penalty
                else:
                    table_only_penalty += penalty
        else:
            table_only_penalty = max(0.0, 100.0 - new_score)

        node_penalties[source_node_id] = {
            "cols": col_penalties,
            "table_only_penalty": table_only_penalty
        }

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

                # Query active parents of the child
                parents_edges = db.query(LineageEdge).filter(
                    LineageEdge.target_node_id == child_id,
                    LineageEdge.valid_to == None
                ).all()

                # Calculate column-level penalties for child
                child_cols_penalties = {}
                child_cols_list = list(child_node.meta.get("columns", {}).keys()) if child_node.meta else []
                
                # Fetch active column lineage edges for this child
                col_edges = db.query(LineageColumnEdge).filter(
                    LineageColumnEdge.target_node_id == child_id,
                    LineageColumnEdge.valid_to == None
                ).all()

                # Map child columns to their parent columns
                col_edges_map = {}
                for ce in col_edges:
                    col_edges_map.setdefault(ce.target_column, []).append((ce.source_node_id, ce.source_column))

                if not child_cols_list:
                    child_cols_list = list(col_edges_map.keys())

                max_lineage_penalty = 0.0

                for col in child_cols_list:
                    col_penalty = 0.0
                    upstream_parents = col_edges_map.get(col, [])
                    for parent_id, parent_col in upstream_parents:
                        parent_data = node_penalties.get(parent_id)
                        if parent_data:
                            parent_col_penalty = parent_data["cols"].get(parent_col, 0.0)
                            col_penalty = max(col_penalty, parent_col_penalty * DECAY_FACTOR)
                            col_penalty = max(col_penalty, parent_data["table_only_penalty"] * DECAY_FACTOR)

                    if not upstream_parents:
                        for pe in parents_edges:
                            p_data = node_penalties.get(pe.source_node_id)
                            if p_data:
                                parent_overall_penalty = p_data["table_only_penalty"]
                                if p_data["cols"]:
                                    parent_overall_penalty = max(parent_overall_penalty, max(p_data["cols"].values()))
                                col_penalty = max(col_penalty, parent_overall_penalty * DECAY_FACTOR)

                    if col_penalty > 0.0:
                        child_cols_penalties[col] = col_penalty
                        if col_penalty > max_lineage_penalty:
                            max_lineage_penalty = col_penalty

                if not child_cols_list:
                    for pe in parents_edges:
                        p_data = node_penalties.get(pe.source_node_id)
                        if p_data:
                            parent_overall_penalty = p_data["table_only_penalty"]
                            if p_data["cols"]:
                                parent_overall_penalty = max(parent_overall_penalty, max(p_data["cols"].values()))
                            propagated = parent_overall_penalty * DECAY_FACTOR
                            if propagated > max_lineage_penalty:
                                max_lineage_penalty = propagated

                lineage_penalty = min(max_lineage_penalty, MAX_PENALTY_LIMIT)

                # Fetch child's own independent base score from trust_scores table
                child_table_name = child_id.split(".")[-1]
                latest_ts = db.query(TrustScore).filter(
                    TrustScore.table_name == child_table_name
                ).order_by(TrustScore.created_at.desc()).first()

                if latest_ts:
                    base_score = float(100 - (
                        latest_ts.contract_penalty +
                        latest_ts.freshness_penalty +
                        latest_ts.volume_penalty +
                        latest_ts.anomaly_penalty +
                        latest_ts.dbt_penalty
                    ))
                else:
                    base_score = 100.0

                final_score = max(0.0, base_score - lineage_penalty)
                child_node.trust_score = final_score
                child_node.last_updated_at = datetime.now(timezone.utc)

                new_meta = dict(child_node.meta or {})
                new_meta["lineage_penalty"] = lineage_penalty
                new_meta["base_score"] = base_score
                new_meta["column_penalties"] = {col: round(val, 2) for col, val in child_cols_penalties.items() if val > 0}
                child_node.meta = new_meta

                node_penalties[child_id] = {
                    "cols": child_cols_penalties,
                    "table_only_penalty": max(0.0, base_score - 100.0)
                }

                queue.append(child_id)

        db.commit()
        logger.info("Column-level health score propagation completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to propagate health score for {source_node_id}",
            exc_info=True,
            extra={"source_node_id": source_node_id}
        )
        raise

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
