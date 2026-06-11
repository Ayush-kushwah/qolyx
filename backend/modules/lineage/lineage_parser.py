import ast
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqllineage.runner import LineageRunner

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge, LineageEdgeHistory

logger = logging.getLogger("qolyx.lineage.parser")


class PythonETLVisitor(ast.NodeVisitor):
    """AST visitor to discover SQL strings and table dependencies in Python ETL code."""

    def __init__(self) -> None:
        self.sources: Set[str] = set()
        self.targets: Set[str] = set()
        self.sql_queries: List[str] = []

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            val = node.value.strip()
            # Basic SQL detection keyword patterns
            if val.upper().startswith(("SELECT", "INSERT", "UPDATE", "WITH", "CREATE")):
                self.sql_queries.append(val)
        self.generic_visit(node)

    def visit_Str(self, node: Any) -> None:
        # Backward compatibility for Python < 3.8
        val = getattr(node, "s", "").strip()
        if val.upper().startswith(("SELECT", "INSERT", "UPDATE", "WITH", "CREATE")):
            self.sql_queries.append(val)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        ast_Str = getattr(ast, "Str", None)

        # Detect common SQL/ETL reading and writing APIs (Pandas, PySpark, etc.)
        if func_name in ("read_sql", "read_sql_query", "read_sql_table", "execute"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self.sql_queries.append(node.args[0].value)
            elif node.args and ast_Str and isinstance(node.args[0], ast_Str):
                self.sql_queries.append(node.args[0].s)
        elif func_name in ("read_table", "table"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self.sources.add(node.args[0].value)
            elif node.args and ast_Str and isinstance(node.args[0], ast_Str):
                self.sources.add(node.args[0].s)
        elif func_name in ("to_sql", "saveAsTable", "write_table"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self.targets.add(node.args[0].value)
            elif node.args and ast_Str and isinstance(node.args[0], ast_Str):
                self.targets.add(node.args[0].s)
            
            # Check keywords e.g. name="table_name"
            for kw in node.keywords:
                if kw.arg in ("name", "table_name") and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    self.targets.add(kw.value.value)
                elif kw.arg in ("name", "table_name") and ast_Str and isinstance(kw.value, ast_Str):
                    self.targets.add(kw.value.s)

        self.generic_visit(node)


def parse_sql_lineage(sql_text: str, file_path: str) -> List[LineageEdge]:
    """Parse table dependencies from SQL text using sqllineage and sqlglot.

    Returns a list of LineageEdge objects representing the dependencies.
    """
    edges: List[LineageEdge] = []
    try:
        runner = LineageRunner(sql_text)
        source_tables = [str(t) for t in runner.source_tables]
        target_tables = [str(t) for t in runner.target_tables]

        # Fallback to sqlglot to capture target tables for simple insert/create queries if sqllineage is empty
        if not target_tables:
            import sqlglot
            from sqlglot import exp
            try:
                parsed = sqlglot.parse_one(sql_text)
                if isinstance(parsed, exp.Create) and parsed.args.get("this"):
                    target_tables.append(parsed.this.sql())
                elif isinstance(parsed, exp.Insert) and parsed.args.get("this"):
                    target_tables.append(parsed.this.sql())
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        for target in target_tables:
            for source in source_tables:
                edge = LineageEdge(
                    id=uuid.uuid4(),
                    source_node_id=source.strip(),
                    target_node_id=target.strip(),
                    edge_type="depends_on",
                    valid_from=now,
                    valid_to=None
                )
                edges.append(edge)
    except Exception as e:
        logger.error(
            f"Failed to parse SQL lineage for file {file_path}",
            exc_info=True,
            extra={"file_path": file_path}
        )
    return edges


def parse_python_lineage(python_code: str, file_path: str) -> List[LineageEdge]:
    """Parse lineage dependencies from a Python script by analyzing AST patterns and embedded SQL."""
    edges: List[LineageEdge] = []
    try:
        tree = ast.parse(python_code)
        visitor = PythonETLVisitor()
        visitor.visit(tree)

        # 1. Process nested SQL strings
        for sql_query in visitor.sql_queries:
            edges.extend(parse_sql_lineage(sql_query, file_path))

        # 2. Add edges for Panda/Spark ETL method calls
        now = datetime.now(timezone.utc)
        for target in visitor.targets:
            for source in visitor.sources:
                edge = LineageEdge(
                    id=uuid.uuid4(),
                    source_node_id=source.strip(),
                    target_node_id=target.strip(),
                    edge_type="depends_on",
                    valid_from=now,
                    valid_to=None
                )
                edges.append(edge)
    except Exception as e:
        logger.error(
            f"Failed to parse Python AST lineage for file {file_path}",
            exc_info=True,
            extra={"file_path": file_path}
        )
    return edges


def parse_dbt_manifest(manifest_path: str) -> Tuple[List[LineageNode], List[LineageEdge]]:
    """Parse dbt manifest.json to extract model/source metadata and dependency edges."""
    nodes: List[LineageNode] = []
    edges: List[LineageEdge] = []
    try:
        if not os.path.exists(manifest_path):
            logger.warning(
                f"dbt manifest file not found; skipping dbt lineage parse",
                extra={"manifest_path": manifest_path}
            )
            return nodes, edges

        with open(manifest_path) as f:
            manifest = json.load(f)

        manifest_nodes = manifest.get("nodes", {})
        manifest_sources = manifest.get("sources", {})
        now = datetime.now(timezone.utc)

        # 1. Process models, seeds, tests, exposures
        for unique_id, data in manifest_nodes.items():
            resource_type = data.get("resource_type")
            if resource_type not in ("model", "seed", "test", "exposure"):
                continue

            name = data.get("name")
            schema = data.get("schema")
            database = data.get("database")
            materialized = data.get("config", {}).get("materialized")
            owner = data.get("meta", {}).get("owner") or data.get("config", {}).get("owner")
            description = data.get("description")
            meta = data.get("meta", {})

            node = LineageNode(
                id=uuid.uuid4(),
                node_id=unique_id,
                name=name,
                type=resource_type,
                schema=schema,
                database=database,
                materialized_type=materialized,
                owner=owner,
                description=description,
                meta=meta,
                trust_score=100.0,
                last_updated_at=now,
                created_at=now,
                updated_at=now
            )
            nodes.append(node)

            # Map dependencies
            depends_on_nodes = data.get("depends_on", {}).get("nodes", [])
            for dep_id in depends_on_nodes:
                edge = LineageEdge(
                    id=uuid.uuid4(),
                    source_node_id=dep_id,
                    target_node_id=unique_id,
                    edge_type="depends_on",
                    valid_from=now,
                    valid_to=None
                )
                edges.append(edge)

        # 2. Process sources
        for unique_id, data in manifest_sources.items():
            name = data.get("name")
            schema = data.get("schema")
            database = data.get("database")
            description = data.get("description")
            meta = data.get("meta", {})
            owner = meta.get("owner")

            node = LineageNode(
                id=uuid.uuid4(),
                node_id=unique_id,
                name=name,
                type="source",
                schema=schema,
                database=database,
                materialized_type=None,
                owner=owner,
                description=description,
                meta=meta,
                trust_score=100.0,
                last_updated_at=now,
                created_at=now,
                updated_at=now
            )
            nodes.append(node)

    except Exception as e:
        logger.error(
            f"Failed to parse dbt manifest from {manifest_path}",
            exc_info=True,
            extra={"manifest_path": manifest_path}
        )
    return nodes, edges


def parse_warehouse_tables(db: Session) -> List[LineageNode]:
    """Read the current warehouse metadata from the database catalogs (information_schema/sqlite_master)."""
    nodes: List[LineageNode] = []
    try:
        bind = db.get_bind()
        dialect = bind.dialect.name
        now = datetime.now(timezone.utc)

        if dialect == "sqlite":
            query = text("SELECT name, tbl_name FROM sqlite_master WHERE type='table'")
            result = db.execute(query).fetchall()
            for row in result:
                table_name = str(row[0])
                if table_name.startswith("sqlite_") or table_name.startswith("alembic_"):
                    continue

                node = LineageNode(
                    id=uuid.uuid4(),
                    node_id=table_name,
                    name=table_name,
                    type="warehouse_table",
                    schema="main",
                    database="local",
                    materialized_type="table",
                    description=f"Local SQLite database table: {table_name}",
                    trust_score=100.0,
                    last_updated_at=now,
                    created_at=now,
                    updated_at=now
                )
                nodes.append(node)
        else:
            query = text("""
                SELECT table_schema, table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            """)
            result = db.execute(query).fetchall()
            for row in result:
                schema_name = str(row[0])
                table_name = str(row[1])
                table_type = str(row[2])
                node_id = f"{schema_name}.{table_name}"

                node = LineageNode(
                    id=uuid.uuid4(),
                    node_id=node_id,
                    name=table_name,
                    type="warehouse_table",
                    schema=schema_name,
                    database=str(bind.url.database) if bind.url else None,
                    materialized_type="table" if "VIEW" not in table_type.upper() else "view",
                    description=f"Warehouse catalog table: {node_id}",
                    trust_score=100.0,
                    last_updated_at=now,
                    created_at=now,
                    updated_at=now
                )
                nodes.append(node)
    except Exception as e:
        logger.error("Failed to parse warehouse tables catalog", exc_info=True)
    return nodes


def sync_all_lineage(db: Session) -> None:
    """Orchestrates all lineage parsers and synchronizes the parsed lineage nodes and edges into the database.

    Maintains temporal tracking of edges using valid_from/valid_to fields.
    """
    logger.info(
        "Initializing Qolyx Lineage Parsing Engine. "
        "Parsing mode: Hybrid Deterministic (LLM-enhanced parser configuration options coming soon)."
    )

    try:
        # 1. Parse DBT manifest
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        manifest_path = os.path.join(workspace_root, "dbt_project", "target", "manifest.json")
        dbt_nodes, dbt_edges = parse_dbt_manifest(manifest_path)
        logger.info(f"Parsed {len(dbt_nodes)} nodes and {len(dbt_edges)} edges from dbt manifest.")

        # 2. Parse warehouse tables
        warehouse_nodes = parse_warehouse_tables(db)
        logger.info(f"Parsed {len(warehouse_nodes)} warehouse catalog nodes.")

        # 3. Parse scripts (discovered in project folders)
        script_edges: List[LineageEdge] = []
        try:
            # We recursively find SQL and Python files in python ETL / airflow directories
            # (Completed script parser integrations will plug directly here)
            from backend.modules.lineage.script_parser import parse_all_scripts
            script_edges = parse_all_scripts(workspace_root)
            logger.info(f"Parsed {len(script_edges)} lineage edges from ad-hoc ETL scripts.")
        except ImportError:
            logger.debug("Script parser module not implemented yet; skipping ad-hoc script parse.")

        # Compile all parsed nodes and edges
        all_nodes = dbt_nodes + warehouse_nodes
        all_edges = dbt_edges + script_edges

        # Dedup nodes by node_id (preferring DBT models over basic warehouse table metadata)
        unique_nodes_map: Dict[str, LineageNode] = {}
        for n in all_nodes:
            if n.node_id not in unique_nodes_map or (n.type != "warehouse_table" and unique_nodes_map[n.node_id].type == "warehouse_table"):
                unique_nodes_map[n.node_id] = n

        # Dedup edges by (source_node_id, target_node_id, edge_type)
        unique_edges_map: Dict[Tuple[str, str, str], LineageEdge] = {}
        for e in all_edges:
            # Prevent self-referential edges
            if e.source_node_id == e.target_node_id:
                continue
            key = (e.source_node_id, e.target_node_id, e.edge_type)
            unique_edges_map[key] = e

        now = datetime.now(timezone.utc)

        # 4. Database Sync Node Operations
        logger.info("Synchronizing lineage nodes into database...")
        for node_id, parsed_node in unique_nodes_map.items():
            existing_node = db.query(LineageNode).filter(LineageNode.node_id == node_id).first()
            if existing_node:
                # Update attributes while keeping the existing trust score
                existing_node.name = parsed_node.name
                existing_node.type = parsed_node.type
                existing_node.schema = parsed_node.schema
                existing_node.database = parsed_node.database
                existing_node.materialized_type = parsed_node.materialized_type
                existing_node.owner = parsed_node.owner
                existing_node.description = parsed_node.description
                existing_node.meta = parsed_node.meta
                existing_node.last_updated_at = now
                existing_node.updated_at = now
            else:
                db.add(parsed_node)
        db.flush()  # Flush so node foreign keys are satisfied

        # 5. Database Sync Edge Operations (Temporal tracking)
        logger.info("Synchronizing lineage dependency edges...")
        db_active_edges = db.query(LineageEdge).filter(LineageEdge.valid_to == None).all()
        db_edges_map = {(e.source_node_id, e.target_node_id, e.edge_type): e for e in db_active_edges}

        # Identify edges to deactivate (exist in DB but not parsed)
        for key, db_edge in db_edges_map.items():
            if key not in unique_edges_map:
                # Edge is removed/deactivated
                db_edge.valid_to = now
                db_edge.updated_at = now

                # Record in history table
                history_rec = LineageEdgeHistory(
                    id=uuid.uuid4(),
                    source_node_id=db_edge.source_node_id,
                    target_node_id=db_edge.target_node_id,
                    edge_type=db_edge.edge_type,
                    valid_from=db_edge.valid_from,
                    valid_to=now,
                    recorded_at=now
                )
                db.add(history_rec)

        # Identify edges to activate (parsed but don't exist in active DB)
        for key, parsed_edge in unique_edges_map.items():
            source_id, target_id, edge_type = key
            
            # Verify both source and target nodes exist in DB before adding edges (integrity check)
            source_exists = db.query(LineageNode).filter(LineageNode.node_id == source_id).first()
            target_exists = db.query(LineageNode).filter(LineageNode.node_id == target_id).first()
            if not source_exists or not target_exists:
                # Skip edge if referenced node IDs are missing
                continue

            if key not in db_edges_map:
                # New active edge
                db.add(parsed_edge)

                # Record in history table (currently active history)
                history_rec = LineageEdgeHistory(
                    id=uuid.uuid4(),
                    source_node_id=parsed_edge.source_node_id,
                    target_node_id=parsed_edge.target_node_id,
                    edge_type=parsed_edge.edge_type,
                    valid_from=parsed_edge.valid_from,
                    valid_to=None,  # Active
                    recorded_at=now
                )
                db.add(history_rec)

        db.commit()
        logger.info("Lineage database synchronization completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Failed to synchronize lineage graph database", exc_info=True)
        raise
