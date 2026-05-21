from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger("airflow.dag.qolyx_fda_ingestion")

default_args = {
    "owner": "qolyx",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def execute_fda_ingestion(**context) -> None:
    """Task callable to execute the FDA Adverse Drug Events ingestion."""
    from backend.core.database import SessionLocal
    from backend.modules.ingestion.services import run_ingestion_sync

    logger.info("Starting FDA drug events ingestion task")
    db = SessionLocal()
    try:
        pipeline_run_id = run_ingestion_sync(db, "fda")
        logger.info("FDA drug events ingestion task completed successfully", extra={"pipeline_run_id": str(pipeline_run_id)})
    except Exception as exc:
        logger.error("FDA drug events ingestion task failed", exc_info=True)
        raise
    finally:
        db.close()

with DAG(
    dag_id="qolyx_fda_ingestion",
    default_args=default_args,
    description="Ingests drug adverse events from openFDA API every 5 minutes",
    schedule_interval="*/5 * * * *",
    catchup=False,
    tags=["qolyx", "ingestion", "fda"]
) as dag:

    task_ingest = PythonOperator(
        task_id="ingest_fda_events",
        python_callable=execute_fda_ingestion,
        provide_context=True,
    )
