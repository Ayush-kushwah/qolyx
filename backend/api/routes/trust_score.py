import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.modules.trust_score.service import TrustScoreService
from backend.modules.trust_score.schemas import TrustScoreAggregatedResponse, TrustScoreHistoryResponse

logger = logging.getLogger("qolyx.api.routes.trust_score")

router = APIRouter(prefix="/trust-score", tags=["Trust Score"])


@router.get("/health")
def check_health() -> dict:
    """Check health status of the Trust Score API service."""
    logger.info("Trust Score health check requested")
    return {"status": "ok", "service": "trust-score"}


@router.get("/{pipeline_run_id}", response_model=TrustScoreAggregatedResponse)
def get_trust_score(
    pipeline_run_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> TrustScoreAggregatedResponse:
    """Retrieve the aggregated trust score and breakdown for a specific pipeline run."""
    logger.info(
        "Requesting trust score for pipeline run",
        extra={"pipeline_run_id": str(pipeline_run_id)}
    )
    record = TrustScoreService.get_trust_score_for_run(db, pipeline_run_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trust Score not found for run {pipeline_run_id}"
        )
    return TrustScoreAggregatedResponse.model_validate(record)


@router.get("/table/{table_name}", response_model=TrustScoreHistoryResponse)
def get_trust_score_history(
    table_name: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> TrustScoreHistoryResponse:
    """Retrieve historical trust score records for a given table with pagination."""
    logger.info(
        "Requesting trust score history for table",
        extra={"table_name": table_name, "page": page, "page_size": page_size}
    )
    try:
        history = TrustScoreService.get_trust_score_history(
            db=db,
            table_name=table_name,
            page=page,
            page_size=page_size
        )
        return TrustScoreHistoryResponse.model_validate(history)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
