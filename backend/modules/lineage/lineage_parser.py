import ast
import json
import logging
import os
import uuid
import hashlib
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqllineage.runner import LineageRunner
import sqlglot
from sqlglot import exp
from sqlglot.lineage import lineage

# Import models
from backend.modules.lineage.models import LineageNode, LineageEdge, LineageEdgeHistory, LineageColumnEdge
from backend.core.config import settings

logger = logging.getLogger("qolyx.lineage.parser")

from collections import OrderedDict

class LRUCache(OrderedDict):
    """Simple thread-safe LRU cache with maxsize to prevent memory bloat on long runs."""
    def __init__(self, maxsize=1000, *args, **kwargs):
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)

_COLUMN_LINEAGE_CACHE = LRUCache(maxsize=1000)
_PARSER_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def get_dbt_project_path() -> str:
    """Helper to dynamically resolve dbt project path for local and container environments."""
    dbt_path = getattr(settings, "DBT_PROJECT_PATH", "/app/dbt_project")
    if os.path.exists(dbt_path):
        return dbt_path
    # Fallback to local workspace path
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    local_path = os.path.join(workspace_root, "dbt_project")
    if os.path.exists(local_path):
        return local_path
    return dbt_path


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


def build_schema_catalog(db: Session) -> Dict[str, Any]:
    """Builds a nested schema catalog (depth 3: catalog -> schema -> table -> columns)
    by querying PostgreSQL information_schema directly and parsing the dbt manifest.
    """
    nested_catalog = {}

    def add_to_catalog(catalog_name: str, schema_name: str, table_name: str, columns: Dict[str, str]):
        if not columns:
            columns = {"_dummy": "VARCHAR"}
        c_key = (catalog_name or "qolyx_prod").lower()
        s_key = (schema_name or "public").lower()
        t_key = table_name.lower()

        if c_key not in nested_catalog:
            nested_catalog[c_key] = {}
        if s_key not in nested_catalog[c_key]:
            nested_catalog[c_key][s_key] = {}
        if t_key not in nested_catalog[c_key][s_key]:
            nested_catalog[c_key][s_key][t_key] = {}
        nested_catalog[c_key][s_key][t_key].update(columns)

    # 1. Query PostgreSQL information_schema directly
    db_tables = {}
    try:
        query = text("""
            SELECT table_catalog, table_schema, table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'public_test_results')
        """)
        result = db.execute(query).fetchall()
        for row in result:
            catalog_name = str(row[0]).lower()
            schema_name = str(row[1]).lower()
            table_name = str(row[2]).lower()
            column_name = str(row[3])
            data_type = str(row[4])

            if is_system_table(table_name):
                continue

            # Add to flat name and qualified name mapping for dbt resolution
            db_tables.setdefault(table_name, {})[column_name] = data_type
            db_tables.setdefault(f"{schema_name}.{table_name}", {})[column_name] = data_type
            
            # Add to nested catalog
            add_to_catalog(catalog_name, schema_name, table_name, {column_name: data_type})
    except Exception as e:
        logger.warning(f"Failed to load schemas from PostgreSQL database: {e}")

    # 2. Parse DBT manifest using get_dbt_project_path()
    try:
        dbt_project_path = get_dbt_project_path()
        manifest_path = os.path.join(dbt_project_path, "target", "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            for unique_id, data in manifest.get("nodes", {}).items():
                if data.get("resource_type") in ("model", "seed"):
                    name = data.get("name")
                    schema = data.get("schema")
                    database = data.get("database")
                    
                    columns = {col: col_data.get("data_type") or "VARCHAR" for col, col_data in data.get("columns", {}).items()}
                    if not columns:
                        if schema and f"{schema.lower()}.{name.lower()}" in db_tables:
                            columns = db_tables[f"{schema.lower()}.{name.lower()}"]
                        elif name.lower() in db_tables:
                            columns = db_tables[name.lower()]
                        
                    add_to_catalog(database, schema, name, columns)
                        
            for unique_id, data in manifest.get("sources", {}).items():
                name = data.get("name")
                schema = data.get("schema")
                database = data.get("database")
                
                columns = {col: col_data.get("data_type") or "VARCHAR" for col, col_data in data.get("columns", {}).items()}
                if not columns:
                    if schema and f"{schema.lower()}.{name.lower()}" in db_tables:
                        columns = db_tables[f"{schema.lower()}.{name.lower()}"]
                    elif name.lower() in db_tables:
                        columns = db_tables[name.lower()]
                
                add_to_catalog(database, schema, name, columns)
    except Exception as e:
        logger.warning(f"Failed to load schemas from DBT manifest: {e}")
        
    return nested_catalog


def _execute_sqlglot_lineage(sql_clean: str, target_col: str, schema: Dict[str, Any]) -> List[Tuple[str, str, Optional[str]]]:
    """Runs sqlglot lineage in worker thread to prevent hanging on large queries."""
    edges = []
    try:
        node = lineage(target_col, sql_clean, schema=schema, dialect="postgres")
        for n in node.walk():
            if not n.downstream:
                parts = n.name.split(".")
                if len(parts) >= 2:
                    src_table = parts[0]
                    src_column = ".".join(parts[1:])
                    # Transformation rule
                    rule = None
                    if n.expression and not isinstance(n.expression, exp.Placeholder):
                        rule = str(n.expression)[:500]
                    edges.append((src_table, src_column, rule))
                elif len(parts) == 1:
                    src_column = parts[0]
                    rule = None
                    if n.expression and not isinstance(n.expression, exp.Placeholder):
                        rule = str(n.expression)[:500]
                    edges.append(("", src_column, rule))
    except Exception as e:
        logger.debug(f"sqlglot failed to parse lineage for column '{target_col}': {e}")
    return edges


def parse_sql_column_lineage(
    sql_text: str,
    target_table: str,
    schema: Dict[str, Any],
    timeout_sec: float = 2.0
) -> List[Tuple[str, str, str, str, Optional[str]]]:
    """Parse column dependencies using sqlglot with caching, timeout safety, and rule extraction.
    
    Returns a list of tuples: (source_table, source_column, target_table, target_column, rule)
    """
    # 1. Clean query quotes
    sql_clean = sql_text.replace('"', '').replace('`', '')
    
    # 2. Check cache
    query_hash = hashlib.sha256(sql_clean.encode("utf-8")).hexdigest()
    cache_key = f"{query_hash}_{target_table}"
    if cache_key in _COLUMN_LINEAGE_CACHE:
        return _COLUMN_LINEAGE_CACHE[cache_key]
        
    column_edges = []
    
    try:
        parsed = sqlglot.parse_one(sql_clean, read="postgres")
        select_expr = parsed if isinstance(parsed, exp.Select) else parsed.find(exp.Select)
        
        target_cols = []
        if select_expr and isinstance(select_expr, exp.Select):
            for select in select_expr.expressions:
                if isinstance(select, exp.Alias):
                    target_cols.append(select.alias)
                elif isinstance(select, exp.Column):
                    target_cols.append(select.name)
        
        clean_target_table = target_table.split(".")[-1]
        
        for col in target_cols:
            future = _PARSER_EXECUTOR.submit(_execute_sqlglot_lineage, sql_clean, col, schema)
            try:
                results = future.result(timeout=timeout_sec)
                for src_table, src_column, rule in results:
                    clean_src_table = src_table if src_table else ""
                    column_edges.append((clean_src_table, src_column, clean_target_table, col, rule))
            except concurrent.futures.TimeoutError:
                logger.warning(f"sqlglot column lineage parsing timed out for target column '{col}'")
            except Exception as e:
                logger.error(f"sqlglot error parsing column '{col}': {e}")
                
    except Exception as e:
        logger.error(f"Failed to parse SELECT structure in SQL text: {e}")
        
    _COLUMN_LINEAGE_CACHE[cache_key] = column_edges
    return column_edges


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

        # 1. Process models, seeds, exposures
        for unique_id, data in manifest_nodes.items():
            resource_type = data.get("resource_type")
            if resource_type not in ("model", "seed", "exposure"):
                continue

            name = data.get("name")
            schema = data.get("schema")
            
            # Filter out any tests/system/public models/seeds/exposures
            schema_lower = schema.lower() if schema else ""
            if schema_lower in ("public", "public_test_results", "pg_catalog", "information_schema"):
                continue
            if is_system_table(name) or is_system_table(unique_id):
                continue
            original_path = data.get("original_file_path", "")
            if "test" in original_path.lower():
                continue

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
            
            # Filter out any sources in system schemas
            schema_lower = schema.lower() if schema else ""
            if schema_lower in ("public_test_results", "pg_catalog", "information_schema"):
                continue
            if is_system_table(name) or is_system_table(unique_id):
                continue

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


def is_system_table(table_name: str) -> bool:
    name_lower = table_name.lower()
    system_prefixes = ("lineage_", "sqlite_", "alembic_")
    system_tables = {
        "contracts", "contract_violations", "anomaly_baselines",
        "anomaly_detections", "anomaly_feedback", "trust_scores", "alert_configs",
        "escalation_policies", "oncall_rotations", "incidents", "incident_comments",
        "incident_rcas", "incident_timeline", "system_settings", "integration_connections",
        "users", "user_api_keys", "user_login_history", "user_sessions",
        "user_llm_providers", "test_results", "alembic_version"
    }
    return any(name_lower.startswith(p) for p in system_prefixes) or name_lower in system_tables


def parse_warehouse_tables(db: Session) -> List[LineageNode]:
    """Read the current warehouse metadata from the database catalogs (information_schema)."""
    nodes: List[LineageNode] = []
    try:
        bind = db.get_bind()
        now = datetime.now(timezone.utc)

        query = text("""
            SELECT table_schema, table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'public', 'public_test_results')
        """)
        result = db.execute(query).fetchall()
        for row in result:
            schema_name = str(row[0])
            table_name = str(row[1])
            if is_system_table(table_name):
                continue
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
        # 1. Parse DBT manifest using get_dbt_project_path()
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        dbt_project_path = get_dbt_project_path()
        manifest_path = os.path.join(dbt_project_path, "target", "manifest.json")
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

        # Dedup nodes by (schema, name) (preferring DBT models/seeds over basic warehouse tables)
        unique_nodes_map: Dict[str, LineageNode] = {}
        node_by_schema_and_name: Dict[Tuple[str, str], LineageNode] = {}
        for n in all_nodes:
            # Filter out system, test and public schema nodes
            schema_lower = n.schema.lower() if n.schema else ""
            if schema_lower in ("public_test_results", "pg_catalog", "information_schema"):
                continue
            if schema_lower == "public" and n.type != "source":
                continue
            if is_system_table(n.name) or is_system_table(n.node_id):
                continue

            key = (schema_lower, n.name.lower())
            if key not in node_by_schema_and_name:
                node_by_schema_and_name[key] = n
            else:
                existing = node_by_schema_and_name[key]
                # Prefer DBT models/seeds over raw warehouse_table
                if n.type != "warehouse_table" and existing.type == "warehouse_table":
                    node_by_schema_and_name[key] = n

        # Populate unique_nodes_map with the deduplicated nodes
        for n in node_by_schema_and_name.values():
            unique_nodes_map[n.node_id] = n

        # Dedup edges by (source_node_id, target_node_id, edge_type)
        unique_edges_map: Dict[Tuple[str, str, str], LineageEdge] = {}
        for e in all_edges:
            # Prevent self-referential edges
            if e.source_node_id == e.target_node_id:
                continue
            # Filter out edges where source or target is not in unique_nodes_map
            if e.source_node_id not in unique_nodes_map or e.target_node_id not in unique_nodes_map:
                continue
            key = (e.source_node_id, e.target_node_id, e.edge_type)
            unique_edges_map[key] = e

        now = datetime.now(timezone.utc)

        # Parse dbt compiled SQL column lineages
        parsed_col_edges = []
        schema_catalog = build_schema_catalog(db)
        
        # Build node resolution map
        table_to_node_id = {}
        for nid, node in unique_nodes_map.items():
            table_to_node_id[node.name.lower()] = nid
            if node.schema:
                table_to_node_id[f"{node.schema.lower()}.{node.name.lower()}"] = nid

        if os.path.exists(manifest_path):
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                for unique_id, data in manifest.get("nodes", {}).items():
                    # Filter out models that are not in our unique_nodes_map
                    if unique_id not in unique_nodes_map:
                        continue
                    if data.get("resource_type") == "model":
                        original_path = data.get("original_file_path")
                        package_name = data.get("package_name")
                        raw_code = data.get("raw_code")
                        
                        sql_text = None
                        if original_path and package_name:
                            compiled_dir = settings.DBT_TARGET_PATH or os.path.join(dbt_project_path, "target")
                            compiled_file = os.path.join(compiled_dir, "compiled", package_name, original_path)
                            if os.path.exists(compiled_file):
                                with open(compiled_file) as sf:
                                    sql_text = sf.read()
                        
                        if not sql_text and raw_code and "{{" not in raw_code:
                            sql_text = raw_code
                            
                        if sql_text:
                            col_edges = parse_sql_column_lineage(sql_text, unique_id, schema_catalog)
                            for src_t, src_c, tgt_t, tgt_c, rule in col_edges:
                                src_nid = None
                                if src_t:
                                    src_t_parts = src_t.lower().split(".")
                                    src_nid = table_to_node_id.get(src_t.lower())
                                    if not src_nid and len(src_t_parts) >= 2:
                                        two_part = f"{src_t_parts[-2]}.{src_t_parts[-1]}"
                                        src_nid = table_to_node_id.get(two_part)
                                    if not src_nid:
                                        src_nid = table_to_node_id.get(src_t_parts[-1])
                                
                                if src_nid:
                                    parsed_col_edges.append(
                                        LineageColumnEdge(
                                            id=uuid.uuid4(),
                                            source_node_id=src_nid,
                                            source_column=src_c,
                                            target_node_id=unique_id,
                                            target_column=tgt_c,
                                            edge_type="direct" if not rule else "derived",
                                            valid_from=now,
                                            valid_to=None,
                                            transformation_rule=rule
                                        )
                                    )
            except Exception as e:
                logger.error(f"Failed parsing DBT manifest models column lineage: {e}", exc_info=True)

        # Dedup parsed column edges
        unique_col_edges_map = {}
        for ce in parsed_col_edges:
            if ce.source_node_id == ce.target_node_id and ce.source_column == ce.target_column:
                continue
            key = (ce.source_node_id, ce.source_column, ce.target_node_id, ce.target_column)
            unique_col_edges_map[key] = ce

        # 4. Database Sync Node Operations
        logger.info("Synchronizing lineage nodes into database...")
        
        # Prune removed/deactivated nodes (e.g. system tables and test nodes)
        db_nodes = db.query(LineageNode).all()
        for db_node in db_nodes:
            if db_node.node_id not in unique_nodes_map:
                # Delete related table-level edges and column-level edges
                db.query(LineageEdge).filter(
                    (LineageEdge.source_node_id == db_node.node_id) |
                    (LineageEdge.target_node_id == db_node.node_id)
                ).delete()
                db.query(LineageEdgeHistory).filter(
                    (LineageEdgeHistory.source_node_id == db_node.node_id) |
                    (LineageEdgeHistory.target_node_id == db_node.node_id)
                ).delete()
                db.query(LineageColumnEdge).filter(
                    (LineageColumnEdge.source_node_id == db_node.node_id) |
                    (LineageColumnEdge.target_node_id == db_node.node_id)
                ).delete()
                db.delete(db_node)
        db.flush()

        for node_id, parsed_node in unique_nodes_map.items():
            existing_node = db.query(LineageNode).filter(LineageNode.node_id == node_id).first()
            if existing_node:
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
        db.flush()

        # ========== ATTACH COLUMN METADATA FROM SCHEMA CATALOG ==========
        logger.info("Attaching column metadata to lineage nodes...")
        
        # Build flat catalog from nested schema_catalog
        flat_catalog = {}
        for catalog_name, schemas in schema_catalog.items():
            for schema_name, tables in schemas.items():
                for table_name, columns in tables.items():
                    # Map by raw table name
                    flat_catalog[table_name] = columns
                    # Map by schema.table
                    flat_catalog[f"{schema_name}.{table_name}"] = columns
                    # Map by catalog.schema.table
                    flat_catalog[f"{catalog_name}.{schema_name}.{table_name}"] = columns

        for node_id, parsed_node in unique_nodes_map.items():
            node_columns = None
            
            # Tries matching by table name, schema.table, and node_id
            name_lower = parsed_node.name.lower()
            schema_lower = parsed_node.schema.lower() if parsed_node.schema else None
            
            # 1. Match by node_id in flat_catalog (if any matches node_id)
            if node_id in flat_catalog:
                node_columns = flat_catalog[node_id]
            # 2. Match by schema.table
            elif schema_lower and f"{schema_lower}.{name_lower}" in flat_catalog:
                node_columns = flat_catalog[f"{schema_lower}.{name_lower}"]
            # 3. Match by table name
            elif name_lower in flat_catalog:
                node_columns = flat_catalog[name_lower]
            # 4. Fallback search: try if any key in flat_catalog is part of node_id or vice versa
            else:
                for key, columns in flat_catalog.items():
                    if key in node_id.lower() or node_id.lower() in key:
                        node_columns = columns
                        break

            if node_columns:
                existing_node = db.query(LineageNode).filter(LineageNode.node_id == node_id).first()
                if existing_node:
                    if not existing_node.meta:
                        existing_node.meta = {}
                    existing_node.meta['columns'] = node_columns
                    existing_node.updated_at = now
                    logger.info(f"Successfully attached {len(node_columns)} columns to node {parsed_node.name} ({node_id})")
        
        db.flush()
        # ========== END COLUMN METADATA ATTACHMENT ==========

        # 5. Database Sync Edge Operations (Temporal tracking)
        logger.info("Synchronizing lineage dependency edges...")
        db_active_edges = db.query(LineageEdge).filter(LineageEdge.valid_to == None).all()
        db_edges_map = {(e.source_node_id, e.target_node_id, e.edge_type): e for e in db_active_edges}

        # Identify edges to deactivate (exist in DB but not parsed)
        for key, db_edge in db_edges_map.items():
            if key not in unique_edges_map:
                db_edge.valid_to = now
                db_edge.updated_at = now

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
            
            source_exists = db.query(LineageNode).filter(LineageNode.node_id == source_id).first()
            target_exists = db.query(LineageNode).filter(LineageNode.node_id == target_id).first()
            if not source_exists or not target_exists:
                continue

            if key not in db_edges_map:
                db.add(parsed_edge)

                history_rec = LineageEdgeHistory(
                    id=uuid.uuid4(),
                    source_node_id=parsed_edge.source_node_id,
                    target_node_id=parsed_edge.target_node_id,
                    edge_type=parsed_edge.edge_type,
                    valid_from=parsed_edge.valid_from,
                    valid_to=None,
                    recorded_at=now
                )
                db.add(history_rec)

        # 6. Database Sync Column Edge Operations (Temporal tracking)
        logger.info("Synchronizing column-level lineage edges...")
        db_active_col_edges = db.query(LineageColumnEdge).filter(LineageColumnEdge.valid_to == None).all()
        db_col_edges_map = {(e.source_node_id, e.source_column, e.target_node_id, e.target_column): e for e in db_active_col_edges}

        # Deactivate removed column edges
        for key, db_col_edge in db_col_edges_map.items():
            if key not in unique_col_edges_map:
                db_col_edge.valid_to = now
                db_col_edge.updated_at = now

        # Activate new column edges
        for key, parsed_col_edge in unique_col_edges_map.items():
            if key not in db_col_edges_map:
                src_exists = db.query(LineageNode).filter(LineageNode.node_id == parsed_col_edge.source_node_id).first()
                tgt_exists = db.query(LineageNode).filter(LineageNode.node_id == parsed_col_edge.target_node_id).first()
                if src_exists and tgt_exists:
                    db.add(parsed_col_edge)

        # 7. Synchronize BI Dashboards & reports
        try:
            from backend.modules.lineage.connectors.connector_registry import sync_bi_dashboards
            sync_bi_dashboards(db)
        except Exception as e:
            logger.error(f"Failed to run BI Dashboard sync step: {e}", exc_info=True)

        db.commit()
        logger.info("Lineage database synchronization completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error("Failed to synchronize lineage graph database", exc_info=True)
        raise