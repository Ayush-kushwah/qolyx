import logging
import os
from typing import List

# Import parser functions and models
from backend.modules.lineage.lineage_parser import parse_sql_lineage, parse_python_lineage
from backend.modules.lineage.models import LineageEdge

logger = logging.getLogger("qolyx.lineage.script_parser")

# Folders to exclude from discovery for performance and cleanliness
EXCLUDED_FOLDERS = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "frontend",
    "dbt_packages",
    "infra",
    ".ai",
    "database",
    "migrations",
    "target",
    "modules",
    "backend",
    "scratch",
    "dbt_project"
}

# Heuristic ETL keywords inside Python files to qualify them as data pipelines
ETL_KEYWORDS = {
    "import pandas",
    "import pyspark",
    "import sqlalchemy",
    "import sqlite3",
    "import psycopg2",
    "from airflow",
    "read_sql",
    "to_sql",
    "execute(",
    ".sql("
}


def discover_sql_files(directory: str) -> List[str]:
    """Recursively search for all .sql files in the directory, skipping excluded folders."""
    sql_files: List[str] = []
    try:
        for root, dirs, files in os.walk(directory):
            # Prune excluded directories in-place to prevent traversing them
            dirs[:] = [d for d in dirs if d not in EXCLUDED_FOLDERS]

            for file in files:
                if file.endswith(".sql"):
                    sql_files.append(os.path.join(root, file))
    except Exception as e:
        logger.error(f"Error discovering SQL files in {directory}: {e}", exc_info=True)
    return sql_files


def discover_python_etl_files(directory: str) -> List[str]:
    """Search for Python files in the directory containing ETL patterns/modules or inside dag folders."""
    etl_files: List[str] = []
    try:
        for root, dirs, files in os.walk(directory):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_FOLDERS]

            # If the folder itself is an airflow_dags or etl folder, we automatically include python files
            is_dag_or_etl_folder = "airflow_dags" in root or "etl" in root or "jobs" in root

            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)

                    if is_dag_or_etl_folder:
                        etl_files.append(full_path)
                        continue

                    # Otherwise, scan file contents for ETL heuristics
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        if any(keyword in content for keyword in ETL_KEYWORDS):
                            etl_files.append(full_path)
                    except Exception as fe:
                        logger.debug(f"Failed to scan Python file {full_path} for ETL keywords: {fe}")
    except Exception as e:
        logger.error(f"Error discovering Python ETL files in {directory}: {e}", exc_info=True)
    return etl_files


def parse_all_scripts(directory: str) -> List[LineageEdge]:
    """Discovers and parses all SQL and Python ETL scripts within the given directory to extract lineage edges."""
    logger.info(
        "Starting script-centric lineage discovery (Zero instrumentation mode active)...",
        extra={"base_directory": directory}
    )

    all_edges: List[LineageEdge] = []

    # 1. Discover and parse SQL scripts
    sql_files = discover_sql_files(directory)
    logger.info(f"Discovered {len(sql_files)} SQL script files for parsing.")
    for sql_file in sql_files:
        try:
            with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
                sql_text = f.read()
            if sql_text.strip():
                edges = parse_sql_lineage(sql_text, sql_file)
                all_edges.extend(edges)
        except Exception as e:
            logger.error(f"Failed to read/parse SQL script: {sql_file}", exc_info=True)

    # 2. Discover and parse Python ETL scripts
    python_files = discover_python_etl_files(directory)
    logger.info(f"Discovered {len(python_files)} Python ETL script files for parsing.")
    for py_file in python_files:
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                py_code = f.read()
            if py_code.strip():
                edges = parse_python_lineage(py_code, py_file)
                all_edges.extend(edges)
        except Exception as e:
            logger.error(f"Failed to read/parse Python script: {py_file}", exc_info=True)

    logger.info(
        "Script-centric lineage discovery completed.",
        extra={"total_edges_found": len(all_edges)}
    )
    return all_edges
