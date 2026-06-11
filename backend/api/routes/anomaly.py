import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.modules.anomaly.models import AnomalyDetection, AnomalyFeedback, SilverAnomalyFeature
from backend.modules.anomaly.baseline_service import AnomalyBaselineService
from backend.modules.anomaly.schemas import (
    AnomalyDetectionResponse,
    AnomalyFeedbackRequest,
    AnomalyFeedbackResponse,
    AnomalyListResponse,
    BaselineTrainingRequest,
    BaselineTrainingResponse,
    BaselineProgress,
    BaselineProgressResponse,
)

logger = logging.getLogger("qolyx.api.routes.anomaly")

router = APIRouter(prefix="/anomaly", tags=["Anomaly"])


@router.get("/detections", response_model=AnomalyListResponse)
def list_detections(
    page: int = 1,
    page_size: int = 10,
    table_name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> AnomalyListResponse:
    """Retrieve a paginated list of anomaly detections."""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater"
        )
    if page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be 1 or greater"
        )

    query = db.query(AnomalyDetection)
    if table_name:
        query = query.filter(AnomalyDetection.table_name == table_name)
        
    total = query.count()
    offset = (page - 1) * page_size
    detections = query.order_by(AnomalyDetection.created_at.desc()).offset(offset).limit(page_size).all()
    
    return AnomalyListResponse(
        detections=[AnomalyDetectionResponse.model_validate(d) for d in detections],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/detections/{detection_id}", response_model=AnomalyDetectionResponse)
def get_detection(detection_id: uuid.UUID, db: Session = Depends(get_db)) -> AnomalyDetectionResponse:
    """Retrieve details of a single anomaly detection by ID."""
    detection = db.query(AnomalyDetection).filter(AnomalyDetection.id == detection_id).first()
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly detection record with ID {detection_id} not found"
        )
    return AnomalyDetectionResponse.model_validate(detection)


@router.get("/detections/run/{pipeline_run_id}", response_model=List[AnomalyDetectionResponse])
def get_detections_for_run(
    pipeline_run_id: uuid.UUID, 
    db: Session = Depends(get_db)
) -> List[AnomalyDetectionResponse]:
    """Retrieve all anomaly detections associated with a specific pipeline run."""
    detections = db.query(AnomalyDetection).filter(AnomalyDetection.pipeline_run_id == pipeline_run_id).all()
    return [AnomalyDetectionResponse.model_validate(d) for d in detections]


@router.post(
    "/detections/{detection_id}/feedback", 
    response_model=AnomalyFeedbackResponse, 
    status_code=status.HTTP_201_CREATED
)
def submit_feedback(
    detection_id: uuid.UUID,
    payload: AnomalyFeedbackRequest,
    db: Session = Depends(get_db)
) -> AnomalyFeedbackResponse:
    """Submit operator feedback for a detected anomaly."""
    detection = db.query(AnomalyDetection).filter(AnomalyDetection.id == detection_id).first()
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly detection record with ID {detection_id} not found"
        )
        
    detection.is_acknowledged = True
    
    feedback = AnomalyFeedback(
        id=uuid.uuid4(),
        anomaly_detection_id=detection_id,
        feedback_type=payload.feedback_type,
        user_notes=payload.user_notes,
        created_by=payload.created_by
    )
    
    # Update is_false_positive flag on the detection record
    if payload.feedback_type == "false_positive":
        detection.is_false_positive = True
    else:
        detection.is_false_positive = False
        
    try:
        detection.updated_at = datetime.now(timezone.utc)
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        db.refresh(detection)
        return AnomalyFeedbackResponse.model_validate(feedback)
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to submit anomaly feedback: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(exc)}"
        )


@router.post("/train", response_model=BaselineTrainingResponse)
def trigger_baseline_training(
    payload: BaselineTrainingRequest,
    db: Session = Depends(get_db)
) -> BaselineTrainingResponse:
    """Manually trigger baseline training for a specific table."""
    try:
        response = AnomalyBaselineService.train_baseline(
            db=db,
            table_name=payload.table_name,
            force_retrain=payload.force_retrain
        )
        return response
    except Exception as exc:
        logger.error(f"Baseline training failed: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Baseline training failed: {str(exc)}"
        )


@router.get("/baseline/progress", response_model=BaselineProgressResponse)
def get_baseline_progress(db: Session = Depends(get_db)) -> BaselineProgressResponse:
    """Retrieve detailed machine learning baseline training progress for all ingestion tables."""
    tables = ["bronze_financial_candles", "bronze_fda_events", "bronze_github_events"]
    progress_details = {}

    for table in tables:
        try:
            runs_completed = db.query(SilverAnomalyFeature).filter(
                SilverAnomalyFeature.source_name == table
            ).count()
        except Exception as exc:
            logger.error(
                f"Graceful degradation: failed to query SilverAnomalyFeature count for table '{table}': {str(exc)}",
                exc_info=True
            )
            runs_completed = 0

        is_ready = AnomalyBaselineService.is_baseline_ready(db, table)
        
        if is_ready or runs_completed >= 7:
            runs_completed = max(runs_completed, 7)
            estimated_minutes = 0
            is_ready = True
        else:
            remaining_runs = max(0, 7 - runs_completed)
            estimated_minutes = remaining_runs * 5

        progress_details[table] = BaselineProgress(
            runs_completed=runs_completed,
            runs_needed=7,
            is_ready=is_ready,
            estimated_minutes_remaining=estimated_minutes
        )

    return BaselineProgressResponse(**progress_details)


@router.get("/baseline/{table_name}", response_model=Dict[str, Dict[str, Any]])
def get_baseline_stats(
    table_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, Dict[str, Any]]:
    """Retrieve current baseline statistics for a given table."""
    baseline = AnomalyBaselineService.get_baseline(db, table_name)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No baseline statistics found for table '{table_name}'"
        )
        
    return {
        metric: {
            "id": str(b.id),
            "table_name": b.table_name,
            "metric_name": b.metric_name,
            "feature_columns": b.feature_columns,
            "mean": b.mean,
            "std_dev": b.std_dev,
            "model_name": b.model_name,
            "training_run_count": b.training_run_count,
            "last_trained_at": b.last_trained_at.isoformat() if b.last_trained_at else None,
            "decay_factor": b.decay_factor
        }
        for metric, b in baseline.items()
    }


@router.get("/health", response_model=Dict[str, bool])
def check_baseline_health(db: Session = Depends(get_db)) -> Dict[str, bool]:
    """Check if baseline is ready (at least 7 runs) for each ingestion table."""
    tables = ["bronze_financial_candles", "bronze_fda_events", "bronze_github_events"]
    return {table: AnomalyBaselineService.is_baseline_ready(db, table) for table in tables}

