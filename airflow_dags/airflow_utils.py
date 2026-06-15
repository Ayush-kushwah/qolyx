import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from airflow.exceptions import AirflowSkipException

from backend.core.database import SessionLocal
from backend.modules.incidents.models import SystemSettings
from backend.modules.trust_score.models import TrustScore

logger = logging.getLogger("airflow.dag.cooldown_check")

# Map of DAG pipeline name to their database table name
TABLE_NAME_MAP = {
    "finnhub": "bronze_financial_candles",
    "fda": "bronze_fda_events",
    "github": "bronze_github_events",
}

def check_pipeline_cooldown(pipeline_name: str) -> None:
    """Checks if the pipeline has run within its configured cooldown period.
    
    If it has run recently, raises AirflowSkipException to skip downstream tasks.
    """
    logger.info(f"Checking scheduling cooldown for pipeline: {pipeline_name}")
    db: Session = SessionLocal()
    try:
        # 1. Fetch settings from DB
        rec = db.query(SystemSettings).filter(SystemSettings.key == "pipeline_frequency_settings").first()
        run_frequency = 15  # Default fallback
        if rec and rec.value:
            try:
                settings_dict = json.loads(rec.value)
                if pipeline_name in settings_dict:
                    run_frequency = int(settings_dict[pipeline_name].get("run_frequency_minutes", 15))
            except Exception as e:
                logger.error(f"Error parsing pipeline settings: {e}")

        # 2. Get the table name corresponding to the pipeline name
        table_name = TABLE_NAME_MAP.get(pipeline_name, pipeline_name)

        # 3. Query the latest TrustScore run timestamp for this table
        last_run = db.query(TrustScore).filter(
            TrustScore.table_name == table_name
        ).order_by(TrustScore.created_at.desc()).first()

        if last_run:
            last_run_time = last_run.created_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            elapsed_minutes = (now - last_run_time).total_seconds() / 60.0

            logger.info(f"Last run for {pipeline_name} was at {last_run_time} ({elapsed_minutes:.1f} minutes ago). Cooldown interval: {run_frequency} minutes.")
            if elapsed_minutes < run_frequency:
                logger.info(f"Skipping DAG run for {pipeline_name}: cooldown active ({elapsed_minutes:.1f}m elapsed < {run_frequency}m required).")
                raise AirflowSkipException(
                    f"Cooldown active: {elapsed_minutes:.1f}m elapsed < {run_frequency}m required."
                )
        else:
            logger.info(f"No previous runs found for {pipeline_name}; executing ingestion.")

    finally:
        db.close()
