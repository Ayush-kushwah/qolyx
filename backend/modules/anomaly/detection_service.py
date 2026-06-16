import uuid
import logging
import pickle
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy.orm import Session

from backend.core.events import publish
from backend.modules.anomaly.models import AnomalyDetection, SilverAnomalyFeature
from backend.modules.anomaly.isolation_forest_service import IsolationForestService
from backend.modules.anomaly.shap_service import SHAPService

logger = logging.getLogger("qolyx.anomaly")


def _get_pipeline_sensitivity(db: Session, table_name: str) -> str:
    """Helper to query the configured sensitivity (LOW, MEDIUM, HIGH) for a table's pipeline."""
    pipeline_name = "finnhub"
    if "fda" in table_name:
        pipeline_name = "fda"
    elif "github" in table_name:
        pipeline_name = "github"
    else:
        for pk in ["finnhub", "fda", "github"]:
            if pk in table_name:
                pipeline_name = pk
                break
                
    from backend.modules.incidents.models import SystemSettings
    rec = db.query(SystemSettings).filter(SystemSettings.key == "pipeline_frequency_settings").first()
    if rec and rec.value:
        try:
            import json
            settings_dict = json.loads(rec.value)
            if pipeline_name in settings_dict:
                return settings_dict[pipeline_name].get("sensitivity", "MEDIUM")
        except Exception:
            pass
    return "MEDIUM"


def detect_volumetric_anomaly(
    db: Session,
    table_name: str,
    current_row_count: int,
    sensitivity: str = "MEDIUM"
) -> Optional[str]:
    """Calculates the rolling Z-Score for a run's row count and flags statistical anomalies.
    
    Returns the type of anomaly ("volume_spike" or "volume_drop") or None if normal.
    """
    Z_THRESHOLD_MAP = {
        "HIGH": 2.0,    # Most sensitive
        "MEDIUM": 3.0,  # Default
        "LOW": 4.0      # Least sensitive
    }
    z_threshold = Z_THRESHOLD_MAP.get(sensitivity, 3.0)

    # Query the last 30 runs of this table in SilverAnomalyFeature
    historical_runs = db.query(SilverAnomalyFeature).filter(
        SilverAnomalyFeature.source_name == table_name
    ).order_by(SilverAnomalyFeature.run_timestamp.desc()).limit(30).all()

    # Need at least 5 runs to compute a meaningful mean and stddev
    if len(historical_runs) < 5:
        logger.info(f"Insufficient history ({len(historical_runs)}/5 runs) to calculate Z-score for table {table_name}.")
        return None

    row_counts = [run.row_count for run in historical_runs]
    mean = sum(row_counts) / len(row_counts)
    
    variance = sum((x - mean) ** 2 for x in row_counts) / len(row_counts)
    std_dev = variance ** 0.5

    if std_dev == 0.0:
        # If std_dev is 0, any deviation from the historical constant volume is flagged
        if current_row_count != mean:
            return "volume_spike" if current_row_count > mean else "volume_drop"
        return None

    z_score = abs(current_row_count - mean) / std_dev
    logger.info(f"Volumetric check for {table_name}: current={current_row_count}, mean={mean:.1f}, std_dev={std_dev:.1f}, Z-score={z_score:.2f} (threshold={z_threshold})")

    if z_score > z_threshold:
        return "volume_spike" if current_row_count > mean else "volume_drop"

    return None


def _classify_anomaly_type(
    db: Session,
    table_name: str,
    feature_values: Dict[str, Any],
    primary_feature: str
) -> str:
    """Classifies the primary anomaly type based on the feature with the highest importance."""
    if primary_feature == "row_count":
        runs = db.query(SilverAnomalyFeature).filter(
            SilverAnomalyFeature.source_name == table_name
        ).order_by(SilverAnomalyFeature.run_timestamp.desc()).limit(60).all()
        if runs:
            avg_rows = sum(r.row_count for r in runs) / len(runs)
        else:
            avg_rows = 0.0
            
        current_rows = feature_values.get("row_count", 0)
        if current_rows > avg_rows:
            return "volume_spike"
        else:
            return "volume_drop"
    elif primary_feature == "freshness_latency_seconds":
        return "freshness_delay"
    elif primary_feature.startswith("null_rate_"):
        return "null_rate_spike"
        
    return "metric_outlier"


def _check_alert_cooldown(db: Session, table_name: str, cooldown_minutes: int = 60) -> bool:
    """Checks if an anomaly alert was already sent for this table within the cooldown period."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
    recent_alert = db.query(AnomalyDetection).filter(
        AnomalyDetection.table_name == table_name,
        AnomalyDetection.last_alerted_at >= cutoff
    ).first()
    return recent_alert is not None


def detect_anomalies(
    db: Session,
    pipeline_run_id: Any,
    table_name: str,
    feature_values: Dict[str, Any]
) -> Optional[AnomalyDetection]:
    """Runs anomaly detection logic using Isolation Forest and SHAP explainability."""
    if isinstance(pipeline_run_id, str):
        pipeline_run_id = uuid.UUID(pipeline_run_id)

    # 1. Check baseline model readiness
    if not IsolationForestService.is_ready(db, table_name):
        logger.info(
            "Skipping anomaly detection: Isolation Forest model is not ready",
            extra={"table_name": table_name, "pipeline_run_id": str(pipeline_run_id)}
        )
        return None

    # 2. Load model parameters
    params = IsolationForestService.get_model_params(db, table_name)
    if not params or "model_path" not in params:
        logger.warning(
            "Skipping anomaly detection: No model parameters found",
            extra={"table_name": table_name, "pipeline_run_id": str(pipeline_run_id)}
        )
        return None

    model_path = params["model_path"]
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
    except Exception as exc:
        logger.error(
            f"Failed to load Isolation Forest model from disk at {model_path}: {str(exc)}",
            exc_info=True,
            extra={"table_name": table_name, "pipeline_run_id": str(pipeline_run_id)}
        )
        return None

    # 3. Convert feature_values to feature vector
    feature_names = params.get("feature_names")
    if not feature_names:
        logger.warning(
            "Skipping anomaly detection: Feature names not found in baseline parameters",
            extra={"table_name": table_name}
        )
        return None

    vector = []
    for feature in feature_names:
        val = None
        if feature == "row_count":
            val = feature_values.get("row_count")
        elif feature == "freshness_latency_seconds":
            val = feature_values.get("freshness_latency_seconds")
        elif feature.startswith("null_rate_"):
            col = feature[len("null_rate_"):]
            null_rates = feature_values.get("null_rates") or {}
            val = null_rates.get(col)
        elif feature == "mean_close_price":
            val = feature_values.get("mean_close_price")
        elif feature == "total_volume":
            val = feature_values.get("total_volume")
        elif feature == "unique_events_count":
            val = feature_values.get("unique_events_count")
            
        vector.append(float(val) if val is not None else 0.0)

    X = np.array([vector], dtype=float)

    # 4. Predict anomaly label using dynamic sensitivity threshold
    decision_score = float(model.decision_function(X)[0])
    sensitivity = _get_pipeline_sensitivity(db, table_name)
    
    # Fast-Path Volume Check
    current_row_count = feature_values.get("row_count")
    volumetric_anomaly = None
    if current_row_count is not None:
        volumetric_anomaly = detect_volumetric_anomaly(db, table_name, int(current_row_count), sensitivity)
        
    if volumetric_anomaly:
        is_anomaly = True
        logger.warning(
            f"Volumetric statistical anomaly '{volumetric_anomaly}' detected. Fast-pathing alert.",
            extra={
                "table_name": table_name,
                "pipeline_run_id": str(pipeline_run_id),
                "current_row_count": current_row_count,
                "sensitivity": sensitivity
            }
        )
    else:
        SENSITIVITY_OFFSETS = {
            "HIGH": 0.05,    # More sensitive: triggers if decision_score < 0.05 (even minor outliers)
            "MEDIUM": 0.0,   # Default: triggers if decision_score < 0.0
            "LOW": -0.05     # Less sensitive: triggers only if decision_score < -0.05 (extreme outliers only)
        }
        
        threshold = SENSITIVITY_OFFSETS.get(sensitivity, 0.0)
        is_anomaly = decision_score < threshold
        
        if not is_anomaly:
            logger.info(
                "No anomalies detected by Isolation Forest model under current sensitivity parameters",
                extra={
                    "table_name": table_name, 
                    "pipeline_run_id": str(pipeline_run_id),
                    "decision_score": decision_score,
                    "sensitivity": sensitivity,
                    "threshold": threshold
                }
            )
            return None

    # 5. Calculate normalized score
    anomaly_score = IsolationForestService.get_anomaly_score(db, table_name, feature_values)

    # 6. Calculate penalty
    anomaly_penalty = min(int(anomaly_score * 20), 20)

    # 7. Generate SHAP explainability
    feature_importance = SHAPService.explain_anomaly(model, feature_values, feature_names)

    # 8. Classify anomaly type using highest importance feature or use pre-determined fast-path type
    if volumetric_anomaly:
        anomaly_type = volumetric_anomaly
    else:
        if feature_importance:
            primary_feature = max(feature_importance.keys(), key=lambda k: abs(feature_importance[k]))
        else:
            primary_feature = "unknown"
        anomaly_type = _classify_anomaly_type(db, table_name, feature_values, primary_feature)

    # 9. Generate human-readable explanation
    explanation = SHAPService.generate_explanation(feature_importance, anomaly_score, anomaly_type)

    # 10. Check alert cooldown
    is_cooldown = _check_alert_cooldown(db, table_name)
    now = datetime.now(timezone.utc)
    last_alerted_at = now if not is_cooldown else None

    # Save feature_importance inside stored_feature_values
    stored_feature_values = dict(feature_values)
    stored_feature_values["feature_importance"] = feature_importance

    # Create record
    detection = AnomalyDetection(
        id=uuid.uuid4(),
        pipeline_run_id=pipeline_run_id,
        table_name=table_name,
        anomaly_type=anomaly_type,
        anomaly_score=anomaly_score,
        anomaly_penalty=anomaly_penalty,
        feature_values=stored_feature_values,
        explanation=explanation,
        is_acknowledged=False,
        is_false_positive=False,
        last_alerted_at=last_alerted_at,
        created_at=now,
        updated_at=now
    )
    # Check lineage-driven suppression before committing
    try:
        from backend.modules.lineage.anomaly_suppression import check_and_suppress_new_anomaly
        check_and_suppress_new_anomaly(db, detection)
    except Exception as prop_exc:
        logger.error(
            f"Failed to check lineage-driven suppression for table {table_name}",
            exc_info=True
        )

    try:
        db.add(detection)
        db.commit()
        db.refresh(detection)
        
        logger.info(
            "Anomaly detected and recorded via Isolation Forest",
            extra={
                "pipeline_run_id": str(pipeline_run_id),
                "table_name": table_name,
                "anomaly_type": anomaly_type,
                "anomaly_score": anomaly_score,
                "anomaly_penalty": anomaly_penalty,
                "explanation": explanation
            }
        )
        
        # Publish event
        publish(
            "anomaly.detected",
            {
                "id": str(detection.id),
                "pipeline_run_id": str(detection.pipeline_run_id),
                "table_name": detection.table_name,
                "anomaly_type": detection.anomaly_type,
                "anomaly_score": detection.anomaly_score,
                "anomaly_penalty": detection.anomaly_penalty,
                "explanation": detection.explanation,
                "last_alerted_at": detection.last_alerted_at.isoformat() if detection.last_alerted_at else None
            }
        )
        
        return detection
    except Exception as exc:
        db.rollback()
        logger.error(
            "Failed to save anomaly detection record",
            exc_info=True,
            extra={"pipeline_run_id": str(pipeline_run_id), "table_name": table_name}
        )
        raise
