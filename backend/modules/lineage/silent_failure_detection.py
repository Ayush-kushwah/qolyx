import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge
from backend.modules.anomaly.models import AnomalyDetection
from backend.modules.incidents.models import Incident

logger = logging.getLogger("qolyx.lineage.silent_failure")

COOLDOWN_PERIOD_HOURS = 24


def create_silent_failure_incident(
    db: Session, 
    node_id: str, 
    failure_type: str, 
    details: Dict[str, Any]
) -> Incident:
    """Creates a silent data reliability incident in the database to prevent pipeline failures from obscuring data errors."""
    table_name = node_id.split(".")[-1]
    
    # Check if a similar open incident already exists to avoid duplication
    existing = db.query(Incident).filter(
        Incident.table_name == table_name,
        Incident.title.like(f"%Silent Failure: {failure_type.replace('_', ' ').title()}%"),
        Incident.state == "OPEN"
    ).first()
    
    if existing:
        logger.info(f"Open silent failure incident of type '{failure_type}' already exists for table '{table_name}'.")
        return existing

    now = datetime.now(timezone.utc)
    incident_id = uuid.uuid4()
    
    # Create new silent failure incident
    incident = Incident(
        id=incident_id,
        pipeline_run_id=uuid.uuid4(),  # Generate unique placeholder run ID
        table_name=table_name,
        severity="HIGH",
        state="OPEN",
        title=f"Silent Failure: {failure_type.replace('_', ' ').title()} on {table_name}",
        resolution_notes=None,
        created_at=now,
        updated_at=now
    )
    db.add(incident)
    db.flush()
    # Add timeline entry
    from backend.modules.incidents.models import IncidentTimeline
    timeline_entry = IncidentTimeline(
        id=uuid.uuid4(),
        incident_id=incident_id,
        event_type="CREATED",
        event_data={
            "title": f"Silent Failure: {failure_type.replace('_', ' ').title()} on {table_name}",
            "description": f"Silent failure '{failure_type}' detected. Details: {details}"
        },
        created_by="Qolyx Silent Failure Detector",
        created_at=now
    )
    db.add(timeline_entry)
    db.commit()
    
    try:
        from backend.core.events import publish
        publish(
            "incident.created",
            {
                "id": str(incident.id),
                "table_name": incident.table_name,
                "title": incident.title,
                "severity": incident.severity
            }
        )
    except Exception as e:
        logger.error(f"Failed to publish silent failure incident event: {e}")
        
    return incident


def compare_schema(db: Session, node_id: str, actual_schema: Dict[str, str]) -> Dict[str, Any]:
    """Compares the current actual schema against the baselined schema stored in LineageNode.meta.

    Triggers a schema_drift silent failure incident if changes are detected.
    """
    node = db.query(LineageNode).filter(LineageNode.node_id == node_id).first()
    if not node:
        node = db.query(LineageNode).filter(LineageNode.node_id.like(f"%.{node_id}")).first()
        
    if not node:
        logger.warning(
            f"Node not found in lineage; cannot compare schema",
            extra={"node_id": node_id}
        )
        return {"drift_detected": False}

    if not node.meta:
        node.meta = {}

    expected_schema = node.meta.get("columns")
    
    # Auto-baseline schema on first evaluation if expected schema is missing
    if not expected_schema:
        node.meta["columns"] = actual_schema
        node.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            f"Baselined expected schema",
            extra={"node_id": node_id, "columns": list(actual_schema.keys())}
        )
        return {"drift_detected": False, "message": "Baselined expected schema."}

    # Identify added, removed, or type-modified columns
    added = [col for col in actual_schema if col not in expected_schema]
    removed = [col for col in expected_schema if col not in actual_schema]
    modified = {}
    
    for col in actual_schema:
        if col in expected_schema and actual_schema[col] != expected_schema[col]:
            modified[col] = {
                "expected": expected_schema[col],
                "actual": actual_schema[col]
            }

    drift_detected = len(added) > 0 or len(removed) > 0 or len(modified) > 0

    result = {
        "drift_detected": drift_detected,
        "added": added,
        "removed": removed,
        "modified": modified
    }

    if drift_detected:
        logger.warning(
            "Schema drift detected",
            extra={"node_id": node_id, "drift": result}
        )
        create_silent_failure_incident(db, node_id, "schema_drift", result)

    return result


def detect_null_propagation(db: Session, node_id: str) -> Optional[Dict[str, Any]]:
    """Traces recent null rate spikes upstream recursively in the lineage graph.

    Finds the root cause ancestor and creates a null_propagation silent failure incident.
    """
    table_name = node_id.split(".")[-1]
    cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_PERIOD_HOURS)

    # Find the latest null spike anomaly on this table
    anomaly = db.query(AnomalyDetection).filter(
        AnomalyDetection.table_name == table_name,
        AnomalyDetection.anomaly_type == "null_rate_spike",
        AnomalyDetection.created_at >= cooldown_time
    ).order_by(AnomalyDetection.created_at.desc()).first()

    if not anomaly:
        return None

    # Get the column with the highest null spike rate
    null_column = None
    feature_values = anomaly.feature_values or {}
    null_rates = feature_values.get("null_rates", {})
    if null_rates:
        null_column = max(null_rates.keys(), key=lambda k: null_rates[k])

    if not null_column:
        return None

    trace_path = [node_id]
    current_node_id = node_id
    root_cause_node_id = node_id

    # Trace upstream to find parent tables with concurrent null spikes on the same column
    while True:
        edges = db.query(LineageEdge).filter(
            LineageEdge.target_node_id == current_node_id,
            LineageEdge.valid_to == None
        ).all()

        parent_found = False
        for edge in edges:
            parent_id = edge.source_node_id
            parent_table = parent_id.split(".")[-1]

            parent_anomaly = db.query(AnomalyDetection).filter(
                AnomalyDetection.table_name == parent_table,
                AnomalyDetection.anomaly_type == "null_rate_spike",
                AnomalyDetection.created_at >= cooldown_time
            ).first()

            if parent_anomaly:
                p_null_rates = (parent_anomaly.feature_values or {}).get("null_rates", {})
                # If parent also has nulls on the same column
                if p_null_rates.get(null_column, 0.0) > 0.05:
                    trace_path.append(parent_id)
                    current_node_id = parent_id
                    root_cause_node_id = parent_id
                    parent_found = True
                    break

        if not parent_found:
            break

    if len(trace_path) > 1:
        result = {
            "propagation_type": "null_propagation",
            "column": null_column,
            "target": node_id,
            "source_root_cause": root_cause_node_id,
            "path": list(reversed(trace_path))
        }
        create_silent_failure_incident(db, node_id, "null_propagation", result)
        return result

    return None


def detect_duplicate_propagation(db: Session, node_id: str) -> Optional[Dict[str, Any]]:
    """Traces recent duplicate key or volumetric spike anomalies upstream in the lineage graph."""
    table_name = node_id.split(".")[-1]
    cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_PERIOD_HOURS)

    anomaly = db.query(AnomalyDetection).filter(
        AnomalyDetection.table_name == table_name,
        AnomalyDetection.anomaly_type.in_(["duplicate_keys", "volume_spike"]),
        AnomalyDetection.created_at >= cooldown_time
    ).order_by(AnomalyDetection.created_at.desc()).first()

    if not anomaly:
        return None

    trace_path = [node_id]
    current_node_id = node_id
    root_cause_node_id = node_id

    while True:
        edges = db.query(LineageEdge).filter(
            LineageEdge.target_node_id == current_node_id,
            LineageEdge.valid_to == None
        ).all()

        parent_found = False
        for edge in edges:
            parent_id = edge.source_node_id
            parent_table = parent_id.split(".")[-1]

            parent_anomaly = db.query(AnomalyDetection).filter(
                AnomalyDetection.table_name == parent_table,
                AnomalyDetection.anomaly_type.in_(["duplicate_keys", "volume_spike"]),
                AnomalyDetection.created_at >= cooldown_time
            ).first()

            if parent_anomaly:
                trace_path.append(parent_id)
                current_node_id = parent_id
                root_cause_node_id = parent_id
                parent_found = True
                break

        if not parent_found:
            break

    if len(trace_path) > 1:
        result = {
            "propagation_type": "duplicate_propagation",
            "target": node_id,
            "source_root_cause": root_cause_node_id,
            "path": list(reversed(trace_path))
        }
        create_silent_failure_incident(db, node_id, "duplicate_propagation", result)
        return result

    return None


def check_pipeline_freshness_sla(db: Session) -> int:
    """Scan active ingestion pipelines and raise incidents for runs exceeding their freshness SLA.
    
    Returns the number of new silent failure incidents created.
    """
    logger.info("Executing periodic pipeline freshness SLA checks...")
    from backend.modules.incidents.models import SystemSettings
    from backend.modules.trust_score.models import TrustScore
    import json

    # 1. Fetch settings from DB
    rec = db.query(SystemSettings).filter(SystemSettings.key == "pipeline_frequency_settings").first()
    if not rec or not rec.value:
        logger.info("No pipeline frequency settings configurations found in database; using defaults.")
        pipeline_configs = {
            "finnhub": {"run_frequency_minutes": 15},
            "fda": {"run_frequency_minutes": 15},
            "github": {"run_frequency_minutes": 15}
        }
    else:
        try:
            pipeline_configs = json.loads(rec.value)
        except Exception as e:
            logger.error(f"Failed to parse pipeline frequency settings: {e}")
            return 0

    TABLE_NAME_MAP = {
        "finnhub": "bronze_financial_candles",
        "fda": "bronze_fda_events",
        "github": "bronze_github_events",
    }

    incidents_created = 0
    now = datetime.now(timezone.utc)

    for pipeline, config in pipeline_configs.items():
        table_name = TABLE_NAME_MAP.get(pipeline, pipeline)
        run_freq = int(config.get("run_frequency_minutes", 15))
        sla_threshold_minutes = run_freq * 2

        # Query the latest TrustScore run timestamp for this table
        latest_run = db.query(TrustScore).filter(
            TrustScore.table_name == table_name
        ).order_by(TrustScore.created_at.desc()).first()

        if latest_run:
            last_run_time = latest_run.created_at.replace(tzinfo=timezone.utc)
            elapsed_minutes = (now - last_run_time).total_seconds() / 60.0

            logger.info(f"Pipeline {pipeline} elapsed freshness: {elapsed_minutes:.1f}m. SLA: {sla_threshold_minutes}m.")
            if elapsed_minutes > sla_threshold_minutes:
                node_id = f"source.{pipeline}.{table_name}"
                details = {
                    "minutes_since_last_run": round(elapsed_minutes, 1),
                    "sla_threshold_minutes": sla_threshold_minutes,
                    "last_reported_run": last_run_time.isoformat()
                }
                
                # Check if a similar open incident already exists to avoid duplication
                existing = db.query(Incident).filter(
                    Incident.table_name == table_name,
                    Incident.title.like("%Silent Failure: Freshness Sla Violation%"),
                    Incident.state == "OPEN"
                ).first()

                if not existing:
                    logger.warning(f"Pipeline {pipeline} has exceeded its Freshness SLA. Creating silent failure incident...")
                    create_silent_failure_incident(
                        db=db,
                        node_id=node_id,
                        failure_type="freshness_sla_violation",
                        details=details
                    )
                    incidents_created += 1
        else:
            logger.info(f"No previous runs found for pipeline {pipeline}; skipping SLA validation.")

    return incidents_created

