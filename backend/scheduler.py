import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler

from backend.core.database import SessionLocal
from backend.modules.incidents.escalation_service import EscalationService
from backend.modules.incidents.rotation_service import RotationService
from backend.modules.lineage.silent_failure_detection import check_pipeline_freshness_sla

logger = logging.getLogger("qolyx.scheduler")

_scheduler: Optional[BackgroundScheduler] = None


def check_escalation_job() -> None:
    """Scheduled job to check and trigger due incident escalations."""
    logger.info("Running scheduled escalation checks...")
    db = SessionLocal()
    try:
        count = EscalationService.check_escalations(db)
        if count > 0:
            logger.info(f"Escalated {count} incident(s) during scheduled run.")
    except Exception as exc:
        logger.error("Error occurred during scheduled escalation checks", exc_info=True)
    finally:
        db.close()


def check_rotation_job() -> None:
    """Scheduled job to check and perform due developer rotations."""
    logger.info("Running scheduled developer rotation checks...")
    db = SessionLocal()
    try:
        count = RotationService.check_and_rotate(db)
        if count > 0:
            logger.info(f"Rotated {count} schedule(s) during scheduled run.")
    except Exception as exc:
        logger.error("Error occurred during scheduled developer rotation checks", exc_info=True)
    finally:
        db.close()


def check_freshness_job() -> None:
    """Scheduled job to check pipeline freshness SLAs and report delayed runs."""
    logger.info("Running scheduled pipeline freshness SLA checks...")
    db = SessionLocal()
    try:
        count = check_pipeline_freshness_sla(db)
        if count > 0:
            logger.info(f"Created {count} freshness SLA violation incident(s) during scheduled run.")
    except Exception as exc:
        logger.error("Error occurred during scheduled freshness checks", exc_info=True)
    finally:
        db.close()


def start_scheduler() -> None:
    """Initializes and starts the BackgroundScheduler for periodic tasks."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler is already running; skipping initialization.")
        return

    logger.info("Starting background scheduler...")
    _scheduler = BackgroundScheduler()

    # Run check_escalations every 60 seconds
    _scheduler.add_job(check_escalation_job, "interval", seconds=60, id="escalation_check_job")

    # Run check_and_rotate every 3600 seconds (1 hour)
    _scheduler.add_job(check_rotation_job, "interval", seconds=3600, id="rotation_check_job")

    # Run check_pipeline_freshness_sla every 600 seconds (10 minutes)
    _scheduler.add_job(check_freshness_job, "interval", seconds=600, id="freshness_check_job")

    _scheduler.start()
    logger.info("Background scheduler successfully started.")


def shutdown_scheduler() -> None:
    """Gracefully shuts down the background scheduler if it is active."""
    global _scheduler
    if _scheduler is None:
        logger.warning("No active scheduler found to shut down.")
        return

    logger.info("Shutting down background scheduler...")
    try:
        _scheduler.shutdown()
        logger.info("Background scheduler successfully shut down.")
    except Exception as exc:
        logger.error("Error occurred while shutting down background scheduler", exc_info=True)
    finally:
        _scheduler = None


def run_once_for_testing() -> None:
    """Runs scheduled jobs synchronously once for manual testing or diagnostic purposes."""
    logger.info("Running diagnostic jobs synchronously...")
    check_escalation_job()
    check_rotation_job()
    check_freshness_job()
    logger.info("Diagnostic jobs execution completed.")
