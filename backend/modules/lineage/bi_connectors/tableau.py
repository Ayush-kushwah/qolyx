import logging
import time
from typing import Any, Dict, List
import httpx
from backend.modules.lineage.bi_connectors.base import BIConnector

logger = logging.getLogger("qolyx.lineage.bi_connectors.tableau")


class TableauConnector(BIConnector):
    """Tableau API Connector mapping Workbooks and Sheets via GraphQL Metadata API."""

    def __init__(self, server_url: str, access_token: str, token_name: str = "qolyx_token", site_name: str = "") -> None:
        self.server_url = server_url.rstrip("/")
        self.access_token = access_token
        self.token_name = token_name
        self.site_name = site_name
        self.auth_token: str = ""

    def _authenticate(self) -> str:
        """Sign in using Personal Access Token to get auth token."""
        if self.auth_token:
            return self.auth_token

        url = f"{self.server_url}/api/3.10/auth/signin"
        # Tableau sign-in payload structure
        payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.access_token,
                "site": {"contentUrl": self.site_name}
            }
        }

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                self.auth_token = data["credentials"]["token"]
                return self.auth_token
        except Exception as e:
            logger.error(f"Failed to authenticate with Tableau Server: {e}")
            raise

    def _graphql_query(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """Runs a GraphQL query against Tableau Metadata API with retry logic and 5s timeout."""
        token = self._authenticate()
        headers = {
            "X-Tableau-Auth": token,
            "Content-Type": "application/json"
        }
        url = f"{self.server_url}/api/metadata/graphql"
        payload = {"query": query, "variables": variables or {}}

        delay = 1.0
        for attempt in range(3):
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    
                    if resp.status_code == 429:
                        logger.warning(f"Tableau API rate limited (429). Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                        
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning(f"Tableau GraphQL connection failed (attempt {attempt+1}): {e}")
                if attempt == 2:
                    raise
                time.sleep(delay)
                delay *= 2

        raise httpx.HTTPError("Tableau GraphQL requests exhausted and failed.")

    def test_connection(self) -> bool:
        # Tableau metadata query test
        query = "{ workbooks { name } }"
        try:
            self._graphql_query(query)
            return True
        except Exception as e:
            logger.error(f"Tableau connection verification failed: {e}")
            return False

    def fetch_workspaces(self) -> List[Dict[str, Any]]:
        # Tableau projects are equivalent to workspaces
        query = """
        {
          projects {
            id
            name
          }
        }
        """
        try:
            data = self._graphql_query(query)
            return data.get("data", {}).get("projects", [])
        except Exception:
            return [{"id": "default", "name": "Default Project"}]

    def fetch_reports(self, workspace_id: str) -> List[Dict[str, Any]]:
        # Tableau Workbooks
        query = """
        {
          workbooks {
            id
            name
            project { id }
          }
        }
        """
        try:
            data = self._graphql_query(query)
            wbs = data.get("data", {}).get("workbooks", [])
            # Filter by project/workspace
            return [w for w in wbs if w.get("project", {}).get("id") == workspace_id]
        except Exception:
            return []

    def fetch_datasets(self, workspace_id: str) -> List[Dict[str, Any]]:
        # Tableau Embedded/Published datasources
        query = """
        {
          publishedDatasources {
            id
            name
            project { id }
          }
        }
        """
        try:
            data = self._graphql_query(query)
            ds = data.get("data", {}).get("publishedDatasources", [])
            return [d for d in ds if d.get("project", {}).get("id") == workspace_id]
        except Exception:
            return []

    def fetch_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        # Find underlying database tables
        query = """
        query getTables($datasourceId: ID!) {
          publishedDatasources(filter: {id: $datasourceId}) {
            upstreamTables {
              id
              name
            }
          }
        }
        """
        try:
            data = self._graphql_query(query, {"datasourceId": dataset_id})
            ds_list = data.get("data", {}).get("publishedDatasources", [])
            if ds_list:
                return ds_list[0].get("upstreamTables", [])
        except Exception:
            pass
        return []

    def fetch_columns(self, table_id: str) -> List[Dict[str, Any]]:
        query = """
        query getColumns($tableId: ID!) {
          databaseTables(filter: {id: $tableId}) {
            columns {
              id
              name
            }
          }
        }
        """
        try:
            data = self._graphql_query(query, {"tableId": table_id})
            tables = data.get("data", {}).get("databaseTables", [])
            if tables:
                return tables[0].get("columns", [])
        except Exception:
            pass
        return []

    def fetch_dashboards(self) -> List[Dict[str, Any]]:
        # Tableau dashboards (Sheets of type Dashboard)
        query = """
        {
          dashboards {
            id
            name
          }
        }
        """
        try:
            data = self._graphql_query(query)
            return data.get("data", {}).get("dashboards", [])
        except Exception:
            return []

    def fetch_lineage(self, table_name: str) -> List[Dict[str, Any]]:
        # GraphQL to trace Workbooks that consume a specific database table
        query = """
        query getLineage($tableName: String!) {
          databaseTables(filter: {name: $tableName}) {
            id
            name
            downstreamWorkbooks {
              id
              name
              project { name }
            }
          }
        }
        """
        lineage_map = []
        try:
            data = self._graphql_query(query, {"tableName": table_name})
            tables = data.get("data", {}).get("databaseTables", [])
            for t in tables:
                for wb in t.get("downstreamWorkbooks", []):
                    lineage_map.append({
                        "dashboard_id": f"dashboard.tableau.{wb['id']}",
                        "dashboard_name": wb["name"],
                        "workspace": wb.get("project", {}).get("name") or "Default Site",
                        "dataset": t["name"]
                    })
        except Exception as e:
            logger.error(f"Error fetching Tableau lineage: {e}")
        return lineage_map
