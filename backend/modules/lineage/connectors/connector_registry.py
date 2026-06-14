import time
import json
import httpx
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import models
from backend.modules.users.models import IntegrationConnection
from backend.modules.users.utils import decrypt_config
from backend.core.config import settings as app_settings
from backend.modules.lineage.models import LineageNode, LineageEdge

logger = logging.getLogger("qolyx.lineage.bi_connector")


def api_request_with_retry(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] = None,
    json_data: Dict[str, Any] = None,
    timeout: float = 5.0
) -> httpx.Response:
    """Executes an HTTP request to the BI API with a 5.0s timeout and exponential backoff retry for rate limits."""
    delay = 1.0
    for attempt in range(3):
        try:
            with httpx.Client(timeout=timeout) as client:
                if method.upper() == "POST":
                    resp = client.post(url, headers=headers, json=json_data)
                else:
                    resp = client.get(url, headers=headers)
                
                # Check for rate limiting (429 Too Many Requests)
                if resp.status_code == 429:
                    logger.warning(f"Rate limited (429). Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                return resp
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Request timeout/network issue on attempt {attempt+1}: {e}")
            if attempt == 2:
                raise
            time.sleep(delay)
            delay *= 2
    raise httpx.HTTPError("Failed after 3 retries")


def sync_bi_dashboards(db: Session) -> None:
    """Discovers Tableau, Looker, PowerBI, or fallback mock BI dashboards and persists them to the lineage graph."""
    logger.info("Syncing BI Dashboard mappings...")
    now = datetime.now(timezone.utc)
    
    from backend.modules.lineage.bi_connectors.registry import get_all_active_connectors
    
    # 1. Retrieve all active BI connectors
    connectors = get_all_active_connectors(db)
    
    nodes_to_add = []
    edges_to_add = []
    
    # Retrieve all pipeline nodes that could be sources
    source_nodes = db.query(LineageNode).filter(
        LineageNode.type.in_(["model", "source", "seed"])
    ).all()
    
    # Track added dashboards to avoid duplicates
    added_dashboard_ids = set()
    
    for connector in connectors:
        logger.info(f"Syncing dashboards using {connector.__class__.__name__}...")
        try:
            # We trace lineage for each active source/model node
            for node in source_nodes:
                table_name = node.node_id.split(".")[-1]
                mappings = connector.fetch_lineage(table_name)
                for mapping in mappings:
                    dashboard_id = mapping["dashboard_id"]
                    dashboard_name = mapping["dashboard_name"]
                    workspace = mapping.get("workspace", "Default Workspace")
                    dataset = mapping.get("dataset", "Default Dataset")
                    
                    if dashboard_id not in added_dashboard_ids:
                        dash_node = LineageNode(
                            id=uuid.uuid4(),
                            node_id=dashboard_id,
                            name=dashboard_name,
                            type="dashboard",
                            schema=workspace,
                            database=dataset,
                            description=f"Dashboard integrated from {connector.__class__.__name__}.",
                            trust_score=100.0,
                            last_updated_at=now,
                            created_at=now,
                            updated_at=now
                        )
                        nodes_to_add.append(dash_node)
                        added_dashboard_ids.add(dashboard_id)
                        
                    # Add lineage edge
                    edge = LineageEdge(
                        id=uuid.uuid4(),
                        source_node_id=node.node_id,
                        target_node_id=dashboard_id,
                        edge_type="references",
                        valid_from=now,
                        valid_to=None
                    )
                    edges_to_add.append(edge)
        except Exception as e:
            logger.error(f"Failed to sync BI dashboards for {connector.__class__.__name__}: {e}", exc_info=True)
            
    # 2. Prune previous BI nodes and active edges in database
    existing_bi_nodes = db.query(LineageNode).filter(LineageNode.type == "dashboard").all()
    for eb in existing_bi_nodes:
        db.query(LineageEdge).filter(
            (LineageEdge.source_node_id == eb.node_id) |
            (LineageEdge.target_node_id == eb.node_id)
        ).delete()
        db.delete(eb)
    db.flush()
    
    # 3. Save new BI nodes and edges
    for node in nodes_to_add:
        exists = db.query(LineageNode).filter(LineageNode.node_id == node.node_id).first()
        if not exists:
            db.add(node)
    db.flush()
    
    for edge in edges_to_add:
        src_exists = db.query(LineageNode).filter(LineageNode.node_id == edge.source_node_id).first()
        tgt_exists = db.query(LineageNode).filter(LineageNode.node_id == edge.target_node_id).first()
        if src_exists and tgt_exists:
            db.add(edge)
            
    db.commit()
    logger.info(f"Successfully synchronized {len(nodes_to_add)} BI Dashboard nodes.")

