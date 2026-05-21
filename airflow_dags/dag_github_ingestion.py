from datetime import datetime, timedelta
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger("airflow.dag.qolyx_github_ingestion")

default_args = {
    "owner": "qolyx",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def execute_github_ingestion(**context) -> None:
    """Task callable to execute the GitHub Archive events ingestion."""
    from backend.core.database import SessionLocal
    from backend.modules.ingestion.services import run_ingestion_sync

    logger.info("Starting GitHub Archive events ingestion task")
    db = SessionLocal()
    try:
        pipeline_run_id = run_ingestion_sync(db, "github")
        logger.info("GitHub Archive events ingestion task completed successfully", extra={"pipeline_run_id": str(pipeline_run_id)})
    except Exception as exc:
        logger.error("GitHub Archive events ingestion task failed", exc_info=True)
        raise
    finally:
        db.close()

with DAG(
    dag_id="qolyx_github_ingestion",
    default_args=default_args,
    description="Ingests GitHub Archive events every 5 minutes",
    schedule_interval="*/5 * * * *",
    catchup=False,
    tags=["qolyx", "ingestion", "github"]
) as dag:

    task_ingest = PythonOperator(
        task_id="ingest_github_events",
        python_callable=execute_github_ingestion,
        provide_context=True,
    )
