import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.events import redis_client

logger = logging.getLogger("qolyx.health")
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=Dict[str, Any])
def health_check(response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Checks the operational status of core database and Redis backend services."""
    database_status = "ok"
    redis_status = "ok"

    # Check Database connection
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        database_status = "error"
        logger.error(
            "Database health check failed",
            exc_info=True,
            extra={"status": "database_error"},
        )

    # Check Redis connection
    try:
        if not redis_client.ping():
            redis_status = "error"
    except Exception as exc:
        redis_status = "error"
        logger.error(
            "Redis health check failed",
            exc_info=True,
            extra={"status": "redis_error"},
        )

    checks = {"database": database_status, "redis": redis_status}

    # If any service is degraded, return 503 Service Unavailable
    if database_status == "error" or redis_status == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(
            "Health check degraded", extra={"checks": checks, "status": "degraded"}
        )
        return {"status": "degraded", "checks": checks}

    logger.info("Health check passed", extra={"checks": checks, "status": "healthy"})
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }
