from datetime import datetime, timedelta
import logging
import uuid
from typing import Any
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

def execute_fda_ingestion(**context: Any) -> str:
    """Task callable to execute the FDA Adverse Drug Events ingestion."""
    from backend.core.database import SessionLocal
    from backend.modules.ingestion.services import run_ingestion_sync

    logger.info("Starting FDA drug events ingestion task")
    db = SessionLocal()
    try:
        pipeline_run_id = run_ingestion_sync(db, "fda")
        logger.info("FDA drug events ingestion task completed successfully", extra={"pipeline_run_id": str(pipeline_run_id)})
        return str(pipeline_run_id)
    except Exception as exc:
        logger.error("FDA drug events ingestion task failed", exc_info=True)
        raise
    finally:
        db.close()

def execute_dbt_run(**context: Any) -> None:
    """Task callable to execute DBT models and tests for FDA."""
    import subprocess
    from backend.core.database import SessionLocal
    from backend.modules.contracts.services import enforce_pipeline_gate

    pipeline_run_id = context["task_instance"].xcom_pull(task_ids="ingest_fda_events")
    if not pipeline_run_id:
        raise Exception("No pipeline_run_id found in XCom.")

    if isinstance(pipeline_run_id, str):
        pipeline_run_id = uuid.UUID(pipeline_run_id)

    db = SessionLocal()
    try:
        enforce_pipeline_gate(db, pipeline_run_id)
    finally:
        db.close()

    logger.info("Starting DBT transformation and tests for FDA")
    
    commands = [
        ["dbt", "run", "--models", "bronze_fda_events", "silver_fda_events", "gold_fda_severity_stats"],
        ["dbt", "test", "--models", "bronze_fda_events", "--store-failures"]
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

def execute_anomaly_detection(**context: Any) -> None:
    """Task callable to execute anomaly detection using Isolation Forest."""
    from backend.core.database import SessionLocal
    from backend.modules.anomaly.feature_service import get_features_for_run
    from backend.modules.anomaly.detection_service import detect_anomalies

    pipeline_run_id = context["task_instance"].xcom_pull(task_ids="ingest_fda_events")
    if not pipeline_run_id:
        logger.warning("No pipeline_run_id found in XCom.")
        return

    if isinstance(pipeline_run_id, str):
        pipeline_run_id = uuid.UUID(pipeline_run_id)

    db = SessionLocal()
    try:
        feature_values = get_features_for_run(db, pipeline_run_id)
        if feature_values:
            detect_anomalies(db, pipeline_run_id, "bronze_fda_events", feature_values)
        else:
            logger.warning(f"No SilverAnomalyFeature values found for run: {pipeline_run_id}")
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

    task_dbt = PythonOperator(
        task_id="run_dbt_models",
        python_callable=execute_dbt_run,
        provide_context=True,
    )

    task_anomaly = PythonOperator(
        task_id="run_anomaly_detection",
        python_callable=execute_anomaly_detection,
        provide_context=True,
    )

    task_ingest >> task_dbt >> task_anomaly
