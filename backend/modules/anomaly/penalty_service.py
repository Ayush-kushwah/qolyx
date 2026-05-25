import uuid
import logging
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.modules.anomaly.models import AnomalyDetection

logger = logging.getLogger("qolyx.anomaly.penalty_service")


def calculate_penalty(anomaly_score: float) -> int:
    """Maps a 0-1 anomaly score to a 0-20 penalty."""
    try:
        score_val = float(anomaly_score)
    except (ValueError, TypeError):
        logger.error(f"Invalid anomaly_score value: {anomaly_score}")
        return 0
        
    return min(max(int(score_val * 20), 0), 20)


def get_total_penalty_for_run(db: Session, pipeline_run_id: Any) -> int:
    """Sums anomaly_penalty for all detections in the run, capped at 20."""
    if isinstance(pipeline_run_id, str):
        try:
            pipeline_run_id = uuid.UUID(pipeline_run_id)
        except ValueError:
            logger.error(f"Invalid UUID string format for pipeline_run_id: {pipeline_run_id}")
            return 0

    # We sum the penalties of only non-false-positive detections
    total = db.query(func.sum(AnomalyDetection.anomaly_penalty)).filter(
        AnomalyDetection.pipeline_run_id == pipeline_run_id,
        AnomalyDetection.is_false_positive == False
    ).scalar()

    if total is None:
        return 0

    return min(int(total), 20)
