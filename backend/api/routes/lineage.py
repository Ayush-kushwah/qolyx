import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

# Database and Services
from backend.core.database import get_db
from backend.modules.lineage.models import LineageNode, LineageEdge
from backend.modules.lineage.lineage_parser import sync_all_lineage
from backend.modules.lineage.temporal_service import TemporalLineageService
from backend.modules.lineage.health_propagation import get_critical_path, propagate_health_score
from backend.modules.lineage.anomaly_suppression import get_downstream_nodes, suppress_anomaly_for_lineage
from backend.modules.lineage.silent_failure_detection import compare_schema
from backend.modules.anomaly.models import AnomalyDetection

logger = logging.getLogger("qolyx.api.routes.lineage")

router = APIRouter(prefix="/lineage", tags=["Lineage"])


class SuppressPayload(BaseModel):
    reason: str = Field(..., description="Reason for manual anomaly suppression")


def resolve_node_id(db: Session, node_id: str) -> str:
    if "." in node_id:
        return node_id
    matching_nodes = db.query(LineageNode).filter(
        (LineageNode.node_id == node_id) | 
        (LineageNode.node_id.like(f"%.{node_id}"))
    ).all()
    if not matching_nodes:
        return node_id
    for n in matching_nodes:
        if n.type in ("model", "source", "seed"):
            return n.node_id
    return matching_nodes[0].node_id


@router.get("/nodes")
def list_nodes(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search filter for node names/ids"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve a paginated and searchable list of all lineage nodes."""
    try:
        query = db.query(LineageNode)
        if search:
            query = query.filter(
                (LineageNode.name.ilike(f"%{search}%")) |
                (LineageNode.node_id.ilike(f"%{search}%"))
            )
        
        total = query.count()
        nodes = query.order_by(LineageNode.node_id).offset((page - 1) * size).limit(size).all()
        
        import math
        pages = math.ceil(total / size) if total > 0 else 1
        
        return {
            "items": [n.to_dict() for n in nodes],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    except Exception as e:
        logger.error("Failed to list lineage nodes", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving lineage nodes"
        )


@router.get("/nodes/{node_id}")
def get_node_details(node_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get the full metadata, description, and trust score details of a single lineage node."""
    resolved_id = resolve_node_id(db, node_id)
    node = db.query(LineageNode).filter(LineageNode.node_id == resolved_id).first()
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lineage node not found")
    return node.to_dict()


@router.get("/graph/{node_id}")
def get_full_graph(node_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get the active (current) lineage graph (upstream + downstream) for a given node."""
    resolved_id = resolve_node_id(db, node_id)
    now = datetime.now(timezone.utc)
    return TemporalLineageService.get_lineage_at_time(db, resolved_id, now)


@router.get("/graph/temporal/{node_id}")
def get_temporal_graph(
    node_id: str,
    timestamp: str = Query(..., description="ISO timestamp for time travel query"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Time-travel query to get the lineage graph structure as it existed at a specific point in time."""
    try:
        resolved_id = resolve_node_id(db, node_id)
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return TemporalLineageService.get_lineage_at_time(db, resolved_id, dt)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timestamp ISO-8601 format: {val_err}"
        )


@router.get("/diff/{node_id}")
def get_graph_diff(
    node_id: str,
    timestamp1: str = Query(..., description="Starting snapshot ISO timestamp"),
    timestamp2: str = Query(..., description="Ending snapshot ISO timestamp"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Compare lineage graph mutations (added/removed nodes and edges) between two timestamps."""
    try:
        resolved_id = resolve_node_id(db, node_id)
        t1 = datetime.fromisoformat(timestamp1.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(timestamp2.replace("Z", "+00:00"))
        return TemporalLineageService.get_lineage_diff(db, resolved_id, t1, t2)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timestamp ISO-8601 format: {val_err}"
        )


@router.get("/impact/{node_id}")
def get_impact_analysis(node_id: str, db: Session = Depends(get_db)) -> List[str]:
    """Performs impact analysis by listing all downstream tables recursively affected by this node."""
    resolved_id = resolve_node_id(db, node_id)
    return get_downstream_nodes(db, resolved_id)


@router.get("/critical-path/{node_id}")
def get_node_critical_path(node_id: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Identifies the critical upstream path (highest health score penalty chain) for a node."""
    resolved_id = resolve_node_id(db, node_id)
    return get_critical_path(db, resolved_id)


@router.post("/sync")
def sync_lineage_graph(db: Session = Depends(get_db)) -> Dict[str, str]:
    """Triggers the lineage parsing engine to scan project files, AST, and DB schema, updating the graph."""
    try:
        sync_all_lineage(db)
        return {"status": "success", "message": "Lineage sync completed successfully."}
    except Exception as e:
        logger.error("Failed to run lineage sync via API", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lineage sync failed: {str(e)}"
        )


@router.post("/suppress/{anomaly_id}")
def suppress_anomaly(
    anomaly_id: uuid.UUID,
    payload: SuppressPayload,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Marks an anomaly as suppressed, silencing downstream alerts and recording the suppression rationale."""
    anomaly = db.query(AnomalyDetection).filter(AnomalyDetection.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly record not found")
        
    try:
        anomaly.suppressed_by_lineage = True
        anomaly.updated_at = datetime.now(timezone.utc)
        
        # Save suppression explanation in feedback
        from backend.modules.anomaly.models import AnomalyFeedback
        feedback = AnomalyFeedback(
            id=uuid.uuid4(),
            anomaly_detection_id=anomaly.id,
            feedback_type="ACKNOWLEDGED",
            user_notes=f"Lineage Suppression: {payload.reason}",
            created_by="API Operator",
            created_at=datetime.now(timezone.utc)
        )
        db.add(feedback)
        
        # Run downstream suppression cascade
        suppress_anomaly_for_lineage(db, anomaly.table_name, anomaly.id)
        
        db.commit()
        return {"status": "success", "message": f"Anomaly {anomaly_id} suppressed downstream successfully."}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to suppress anomaly {anomaly_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suppress anomaly"
        )


@router.get("/health-propagation/{node_id}")
def show_health_propagation(node_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Calculates and demonstrates how health penalties decay downstream starting from this node."""
    resolved_id = resolve_node_id(db, node_id)
    node = db.query(LineageNode).filter(LineageNode.node_id == resolved_id).first()
        
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lineage node not found")

    downstream_ids = get_downstream_nodes(db, node.node_id)
    propagation_details = []
    
    current_penalty = 100.0 - (node.trust_score or 100.0)
    
    # Trace decay factor per hop for all downstream nodes
    for child_id in downstream_ids:
        # Simplistic distance check (hop count)
        path = db.query(LineageEdge).filter(
            LineageEdge.source_node_id == node.node_id,
            LineageEdge.target_node_id == child_id,
            LineageEdge.valid_to == None
        ).first()
        
        hops = 1 if path else 2  # Default to 2 hops if transitive
        decayed_penalty = min(current_penalty * (0.9 ** hops), 40.0)
        
        child = db.query(LineageNode).filter(LineageNode.node_id == child_id).first()
        
        propagation_details.append({
            "node_id": child_id,
            "name": child.name if child else child_id,
            "hops": hops,
            "base_score": child.meta.get("base_score", 100.0) if child and child.meta else 100.0,
            "propagated_penalty": decayed_penalty,
            "resulting_score": child.trust_score if child else max(0.0, 100.0 - decayed_penalty)
        })

    return {
        "node_id": node.node_id,
        "name": node.name,
        "current_score": node.trust_score,
        "current_penalty": current_penalty,
        "propagation": propagation_details
    }


@router.get("/compare-schema/{node_id}")
def run_schema_comparison(node_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Discovers the actual schema from warehouse tables and runs the schema comparison check against lineage baseline."""
    try:
        resolved_id = resolve_node_id(db, node_id)
        bind = db.get_bind()
        dialect = bind.dialect.name
        actual_schema = {}
        
        table_name = resolved_id.split(".")[-1]
        
        # Query column metadata from database
        if dialect == "sqlite":
            cursor = db.execute(text(f"PRAGMA table_info('{table_name}')"))
            rows = cursor.fetchall()
            for row in rows:
                col_name = str(row[1])
                col_type = str(row[2])
                actual_schema[col_name] = col_type
        else:
            cursor = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table_name
            """), {"table_name": table_name})
            rows = cursor.fetchall()
            for row in rows:
                col_name = str(row[0])
                col_type = str(row[1])
                actual_schema[col_name] = col_type

        if not actual_schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No actual database columns found for table '{table_name}' in warehouse."
            )

        # Run comparison against baselined expected schema
        return compare_schema(db, resolved_id, actual_schema)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed schema comparison API for table {node_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema comparison failed: {str(e)}"
        )
