from datetime import datetime, timedelta
import logging
import uuid
from typing import Any
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger("airflow.dag.qolyx_finnhub_ingestion")

default_args = {
    "owner": "qolyx",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def execute_finnhub_ingestion(**context: Any) -> uuid.UUID:
    """Task callable to execute the Finnhub stock candles ingestion."""
    from backend.core.database import SessionLocal
    from backend.modules.ingestion.services import run_ingestion_sync

    logger.info("Starting Finnhub ingestion task")
    db = SessionLocal()
    try:
        pipeline_run_id = run_ingestion_sync(db, "finnhub")
        logger.info("Finnhub ingestion task completed successfully", extra={"pipeline_run_id": str(pipeline_run_id)})
        return pipeline_run_id
    except Exception as exc:
        logger.error("Finnhub ingestion task failed", exc_info=True)
        raise
    finally:
        db.close()

def execute_dbt_run(**context: Any) -> None:
    """Task callable to execute DBT models and tests for Finnhub."""
    import subprocess
    from backend.core.database import SessionLocal
    from backend.modules.contracts.services import get_violations_for_run, get_total_penalty_for_run

    from backend.core.exceptions import PipelineBlockedException

    pipeline_run_id = context["task_instance"].xcom_pull(task_ids="ingest_finnhub_candles")
    if not pipeline_run_id:
        raise Exception("No pipeline_run_id found in XCom.")

    if isinstance(pipeline_run_id, str):
        pipeline_run_id = uuid.UUID(pipeline_run_id)

    db = SessionLocal()
    try:
        violations = get_violations_for_run(db, pipeline_run_id)
        if violations:
            total_penalty = get_total_penalty_for_run(db, pipeline_run_id)
            for v in violations:
                logger.error(f"Contract violation: {v.violation_type} - {v.description}")
            raise PipelineBlockedException(f"Pipeline BLOCKED: {len(violations)} contract violations. Total penalty: {total_penalty}/40. Fix schema issues and retry.")
    finally:
        db.close()

    logger.info("Starting DBT transformation and tests for Finnhub")
    
    commands = [
        ["dbt", "run", "--models", "bronze_financial_candles", "silver_financial_candles", "gold_daily_market_summary"],
        ["dbt", "test", "--models", "bronze_financial_candles", "--store-failures"]
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
    dag_id="qolyx_finnhub_ingestion",
    default_args=default_args,
    description="Ingests stock candle data from Finnhub API every 5 minutes",
    schedule_interval="*/5 * * * *",
    catchup=False,
    tags=["qolyx", "ingestion", "finnhub"]
) as dag:

    task_ingest = PythonOperator(
        task_id="ingest_finnhub_candles",
        python_callable=execute_finnhub_ingestion,
        provide_context=True,
    )

    task_dbt = PythonOperator(
        task_id="run_dbt_models",
        python_callable=execute_dbt_run,
        provide_context=True,
    )

    task_ingest >> task_dbt
