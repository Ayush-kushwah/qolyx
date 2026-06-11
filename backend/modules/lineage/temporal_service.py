import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge, LineageEdgeHistory

logger = logging.getLogger("qolyx.lineage.temporal")


class TemporalLineageService:
    """Service to handle temporal (time-travel) lineage queries and difference analysis."""

    @staticmethod
    def get_lineage_at_time(db: Session, node_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Returns the complete lineage graph (upstream + downstream) as it existed at the exact timestamp.

        Returns:
            Dict containing:
                - nodes: List of node dict representations active at that time
                - edges: List of active edges at that time
        """
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        logger.info(
            "Fetching temporal lineage graph",
            extra={"node_id": node_id, "timestamp": timestamp.isoformat()}
        )

        try:
            # 1. Downstream recursive query
            downstream_query = text("""
                WITH RECURSIVE downstream_lineage AS (
                    SELECT source_node_id, target_node_id, edge_type, valid_from, valid_to
                    FROM lineage_edge_history
                    WHERE valid_from <= :timestamp
                      AND (valid_to IS NULL OR valid_to >= :timestamp)
                      AND source_node_id = :node_id
                    UNION ALL
                    SELECT e.source_node_id, e.target_node_id, e.edge_type, e.valid_from, e.valid_to
                    FROM lineage_edge_history e
                    INNER JOIN downstream_lineage d ON e.source_node_id = d.target_node_id
                    WHERE e.valid_from <= :timestamp
                      AND (e.valid_to IS NULL OR e.valid_to >= :timestamp)
                )
                SELECT DISTINCT source_node_id, target_node_id, edge_type, valid_from, valid_to FROM downstream_lineage;
            """)

            # 2. Upstream recursive query
            upstream_query = text("""
                WITH RECURSIVE upstream_lineage AS (
                    SELECT source_node_id, target_node_id, edge_type, valid_from, valid_to
                    FROM lineage_edge_history
                    WHERE valid_from <= :timestamp
                      AND (valid_to IS NULL OR valid_to >= :timestamp)
                      AND target_node_id = :node_id
                    UNION ALL
                    SELECT e.source_node_id, e.target_node_id, e.edge_type, e.valid_from, e.valid_to
                    FROM lineage_edge_history e
                    INNER JOIN upstream_lineage u ON e.target_node_id = u.source_node_id
                    WHERE e.valid_from <= :timestamp
                      AND (e.valid_to IS NULL OR e.valid_to >= :timestamp)
                )
                SELECT DISTINCT source_node_id, target_node_id, edge_type, valid_from, valid_to FROM upstream_lineage;
            """)

            # Execute both traversals
            downstream_rows = db.execute(downstream_query, {"timestamp": timestamp, "node_id": node_id}).fetchall()
            upstream_rows = db.execute(upstream_query, {"timestamp": timestamp, "node_id": node_id}).fetchall()

            # Merge results and avoid duplicates
            all_edges: List[Dict[str, Any]] = []
            visited_keys: Set[Tuple[str, str, str]] = set()
            referenced_node_ids: Set[str] = {node_id}

            for row in downstream_rows + upstream_rows:
                src, tgt, etype, v_from, v_to = row[0], row[1], row[2], row[3], row[4]
                key = (src, tgt, etype)
                if key not in visited_keys:
                    visited_keys.add(key)
                    referenced_node_ids.add(src)
                    referenced_node_ids.add(tgt)
                    all_edges.append({
                        "source_node_id": src,
                        "target_node_id": tgt,
                        "edge_type": etype,
                        "valid_from": v_from.isoformat() if hasattr(v_from, "isoformat") else v_from,
                        "valid_to": v_to.isoformat() if hasattr(v_to, "isoformat") else v_to,
                    })

            # Fetch active metadata nodes at that time
            nodes_query = db.query(LineageNode).filter(LineageNode.node_id.in_(referenced_node_ids)).all()
            nodes_list = [n.to_dict() for n in nodes_query]

            return {
                "nodes": nodes_list,
                "edges": all_edges
            }

        except Exception as e:
            logger.error(
                "Failed to run temporal lineage query",
                exc_info=True,
                extra={"node_id": node_id, "timestamp": timestamp.isoformat()}
            )
            return {"nodes": [], "edges": []}

    @staticmethod
    def get_lineage_diff(db: Session, node_id: str, timestamp1: datetime, timestamp2: datetime) -> Dict[str, Any]:
        """Compares the lineage graph of a node between two points in time.

        Shows added/removed nodes and edges.
        """
        # Ensure timezone awareness
        if timestamp1.tzinfo is None:
            timestamp1 = timestamp1.replace(tzinfo=timezone.utc)
        if timestamp2.tzinfo is None:
            timestamp2 = timestamp2.replace(tzinfo=timezone.utc)

        logger.info(
            "Comparing temporal lineage states",
            extra={
                "node_id": node_id,
                "timestamp1": timestamp1.isoformat(),
                "timestamp2": timestamp2.isoformat()
            }
        )

        # Retrieve state at both timestamps
        t1_graph = TemporalLineageService.get_lineage_at_time(db, node_id, timestamp1)
        t2_graph = TemporalLineageService.get_lineage_at_time(db, node_id, timestamp2)

        # Helper set constructions for comparison
        t1_nodes = {n["node_id"]: n for n in t1_graph["nodes"]}
        t2_nodes = {n["node_id"]: n for n in t2_graph["nodes"]}

        t1_edges = {(e["source_node_id"], e["target_node_id"], e["edge_type"]): e for e in t1_graph["edges"]}
        t2_edges = {(e["source_node_id"], e["target_node_id"], e["edge_type"]): e for e in t2_graph["edges"]}

        # 1. Compare Nodes
        added_node_ids = set(t2_nodes.keys()) - set(t1_nodes.keys())
        removed_node_ids = set(t1_nodes.keys()) - set(t2_nodes.keys())

        added_nodes = [t2_nodes[nid] for nid in added_node_ids]
        removed_nodes = [t1_nodes[nid] for nid in removed_node_ids]

        # 2. Compare Edges
        added_edge_keys = set(t2_edges.keys()) - set(t1_edges.keys())
        removed_edge_keys = set(t1_edges.keys()) - set(t2_edges.keys())

        added_edges = [t2_edges[ekey] for ekey in added_edge_keys]
        removed_edges = [t1_edges[ekey] for ekey in removed_edge_keys]

        return {
            "node_id": node_id,
            "timestamp1": timestamp1.isoformat(),
            "timestamp2": timestamp2.isoformat(),
            "nodes": {
                "added": added_nodes,
                "removed": removed_nodes
            },
            "edges": {
                "added": added_edges,
                "removed": removed_edges
            }
        }

    @staticmethod
    def store_lineage_snapshot(db: Session) -> None:
        """Saves a temporal snapshot of all currently active edges into lineage_edge_history.

        Keeps valid_to bounds sync'd with lineage_edges.
        """
        try:
            now = datetime.now(timezone.utc)
            active_edges = db.query(LineageEdge).filter(LineageEdge.valid_to == None).all()

            for edge in active_edges:
                # Check for active record in history
                hist_exists = db.query(LineageEdgeHistory).filter(
                    LineageEdgeHistory.source_node_id == edge.source_node_id,
                    LineageEdgeHistory.target_node_id == edge.target_node_id,
                    LineageEdgeHistory.edge_type == edge.edge_type,
                    LineageEdgeHistory.valid_to == None
                ).first()

                if not hist_exists:
                    # Write new history entry
                    hist_entry = LineageEdgeHistory(
                        id=uuid.uuid4(),
                        source_node_id=edge.source_node_id,
                        target_node_id=edge.target_node_id,
                        edge_type=edge.edge_type,
                        valid_from=edge.valid_from or now,
                        valid_to=None,
                        recorded_at=now
                    )
                    db.add(hist_entry)

            db.commit()
            logger.info("Saved lineage history snapshot successfully.")
        except Exception as e:
            db.rollback()
            logger.error("Failed to save lineage history snapshot", exc_info=True)
            raise
