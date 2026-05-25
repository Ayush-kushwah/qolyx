import uuid
import logging
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from backend.modules.anomaly.models import SilverAnomalyFeature

logger = logging.getLogger("qolyx.anomaly.feature_service")


def calculate_null_rates(row: Any, columns: List[str]) -> Dict[str, float]:
    """Helper to calculate null rates for a set of columns.
    
    If 'row' is a list of records (dicts or objects), calculates the percentage of nulls (0.0 to 100.0) 
    for each column across all records.
    If 'row' is a single record, calculates null rate for that record (0.0 or 100.0).
    """
    if not row:
        return {col: 0.0 for col in columns}
        
    # If it is a list/tuple/iterable of records
    if isinstance(row, (list, tuple)):
        n_records = len(row)
        if n_records == 0:
            return {col: 0.0 for col in columns}
            
        null_counts = {col: 0 for col in columns}
        for record in row:
            for col in columns:
                val = getattr(record, col, None) if not isinstance(record, dict) else record.get(col)
                if val is None:
                    null_counts[col] += 1
        return {col: (100.0 * null_counts[col] / n_records) for col in columns}
    
    # If it is a single record
    res = {}
    for col in columns:
        val = getattr(row, col, None) if not isinstance(row, dict) else row.get(col)
        res[col] = 100.0 if val is None else 0.0
    return res


def get_features_for_run(db: Session, pipeline_run_id: Any) -> Dict[str, Any]:
    """Queries silver_anomaly_features for the specific run.
    
    Args:
        db: Database session.
        pipeline_run_id: The UUID or string ID of the pipeline run.
        
    Returns:
        A dictionary containing the feature attributes or an empty dict if not found.
    """
    if isinstance(pipeline_run_id, str):
        try:
            pipeline_run_id = uuid.UUID(pipeline_run_id)
        except ValueError:
            logger.error(f"Invalid UUID string format for pipeline_run_id: {pipeline_run_id}")
            return {}
        
    feature = db.query(SilverAnomalyFeature).filter(
        SilverAnomalyFeature.pipeline_run_id == pipeline_run_id
    ).first()
    
    if not feature:
        logger.warning(f"No SilverAnomalyFeature found for pipeline_run_id: {pipeline_run_id}")
        return {}
        
    return {
        "pipeline_run_id": feature.pipeline_run_id,
        "source_name": feature.source_name,
        "row_count": feature.row_count,
        "null_rates": feature.null_rates,
        "mean_close_price": feature.mean_close_price,
        "total_volume": feature.total_volume,
        "unique_events_count": feature.unique_events_count,
        "freshness_latency_seconds": feature.freshness_latency_seconds,
        "run_timestamp": feature.run_timestamp,
    }


def get_feature_vector(feature_values: Dict[str, Any], table_name: str) -> List[float]:
    """Returns ordered list of feature values matching the order used in Isolation Forest training."""
    if table_name == "bronze_financial_candles":
        feature_names = [
            "row_count",
            "freshness_latency_seconds",
            "null_rate_symbol",
            "null_rate_close_price",
            "null_rate_volume",
            "null_rate_candle_timestamp",
            "mean_close_price",
            "total_volume"
        ]
    elif table_name == "bronze_fda_events":
        feature_names = [
            "row_count",
            "freshness_latency_seconds",
            "null_rate_drug_name",
            "null_rate_reaction_description",
            "null_rate_serious",
            "null_rate_receipt_date"
        ]
    elif table_name == "bronze_github_events":
        feature_names = [
            "row_count",
            "freshness_latency_seconds",
            "null_rate_event_id",
            "null_rate_event_type",
            "null_rate_repo_name",
            "null_rate_created_at",
            "unique_events_count"
        ]
    else:
        raise ValueError(f"Unknown table name: {table_name}")
        
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
        
    return vector
