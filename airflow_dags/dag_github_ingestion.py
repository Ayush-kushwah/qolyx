from datetime import datetime, timedelta
import logging
from typing import Any
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

def execute_github_ingestion(**context: Any) -> None:
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

def execute_dbt_run(**context: Any) -> None:
    """Task callable to execute DBT models and tests for GitHub."""
    import subprocess

    logger.info("Starting DBT transformation and tests for GitHub")
    
    commands = [
        ["dbt", "run", "--models", "bronze_github_events", "silver_github_events", "gold_github_activity_summary"],
        ["dbt", "test", "--models", "bronze_github_events", "--store-failures"]
    ]
    
    for cmd in commands:
        logger.info(f"Running DBT command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd="/usr/app/dbt_project",
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            logger.info(f"DBT STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"DBT STDERR:\n{result.stderr}")
            
        if result.returncode != 0:
            logger.error(f"DBT command failed with return code {result.returncode}")
            raise Exception(f"DBT command failed: {' '.join(cmd)}")
            
    logger.info("DBT transformation and tests completed successfully")

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

    task_dbt = PythonOperator(
        task_id="run_dbt_models",
        python_callable=execute_dbt_run,
        provide_context=True,
    )

    task_ingest >> task_dbt

