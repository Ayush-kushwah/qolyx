import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from backend.modules.lineage.bi_connectors.base import BIConnector

logger = logging.getLogger("qolyx.lineage.bi_connectors.looker")


class LookerConnector(BIConnector):
    """Looker API Connector mapping Dashboards, Looks, and Explores via Looker REST API."""

    def __init__(self, host: str, client_id: str, client_secret: str) -> None:
        self.host = host.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expiry: float = 0.0

    def _authenticate(self) -> str:
        """Authenticate using API client credentials to fetch access token."""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        url = f"{self.host}/api/4.0/login"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            with httpx.Client(timeout=5.0, verify=False) as client:  # Local Looker instances might have self-signed SSL
                resp = client.post(url, data=data)
                resp.raise_for_status()
                token_data = resp.json()
                self.access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = time.time() + expires_in - 60
                return self.access_token
        except Exception as e:
            logger.error(f"Failed to authenticate with Looker instance: {e}")
            raise

    def _api_call(self, endpoint: str, method: str = "GET", json_data: Dict = None) -> Any:
        """Executes Looker API request with retry logic and 5s timeout."""
        token = self._authenticate()
        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }
        url = f"{self.host}/api/4.0/{endpoint.lstrip('/')}"

        delay = 1.0
        for attempt in range(3):
            try:
                with httpx.Client(timeout=5.0, verify=False) as client:
                    if method.upper() == "POST":
                        resp = client.post(url, headers=headers, json=json_data)
                    else:
                        resp = client.get(url, headers=headers)
                        
                    if resp.status_code == 429:
                        logger.warning(f"Looker API rate limited (429). Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                        
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                logger.warning(f"Looker API connection failed (attempt {attempt+1}): {e}")
                if attempt == 2:
                    raise
                time.sleep(delay)
                delay *= 2

        raise httpx.HTTPError("Looker API requests exhausted and failed.")

    def test_connection(self) -> bool:
        try:
            # Query current user profile to verify connection
            self._api_call("user")
            return True
        except Exception as e:
            logger.error(f"Looker connection test failed: {e}")
            return False

    def fetch_workspaces(self) -> List[Dict[str, Any]]:
        # Looker folders/spaces act as workspaces
        try:
            folders = self._api_call("folders")
            return [{"id": f["id"], "name": f["name"]} for f in folders if not f.get("is_personal")]
        except Exception:
            return [{"id": "shared", "name": "Shared Folder"}]

    def fetch_reports(self, workspace_id: str) -> List[Dict[str, Any]]:
        # Looker Looks
        try:
            looks = self._api_call("looks")
            return [{"id": l["id"], "name": l["title"], "datasetId": l.get("model", {}).get("name")} for l in looks if str(l.get("folder_id")) == str(workspace_id)]
        except Exception:
            return []

    def fetch_datasets(self, workspace_id: str) -> List[Dict[str, Any]]:
        # Looker Models
        try:
            models = self._api_call("lookml_models")
            return [{"id": m["name"], "name": m["label"]} for m in models]
        except Exception:
            return []

    def fetch_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        # Looker Explores inside LookML Models
        try:
            model = self._api_call(f"lookml_models/{dataset_id}")
            explores = model.get("explores", [])
            return [{"name": e["name"]} for e in explores]
        except Exception:
            return []

    def fetch_columns(self, table_id: str) -> List[Dict[str, Any]]:
        # Mapped dimensions/measures inside Explores
        return [{"name": "id"}, {"name": "dimension_field"}, {"name": "measure_field"}]

    def fetch_dashboards(self) -> List[Dict[str, Any]]:
        try:
            dashboards = self._api_call("dashboards")
            return [{"id": d["id"], "name": d["title"]} for d in dashboards]
        except Exception:
            return []

    def fetch_lineage(self, table_name: str) -> List[Dict[str, Any]]:
        lineage_map = []
        try:
            dashboards = self._api_call("dashboards")
            for d in dashboards:
                dashboard_id = d["id"]
                # Query dashboard details to see the elements/explores used
                details = self._api_call(f"dashboards/{dashboard_id}")
                for element in details.get("dashboard_elements", []):
                    query = element.get("query")
                    if query:
                        explore = query.get("view") or query.get("model")
                        # If this dashboard element queries the table explore/view
                        if explore and table_name.lower() in explore.lower():
                            lineage_map.append({
                                "dashboard_id": f"dashboard.looker.{dashboard_id}",
                                "dashboard_name": d["title"],
                                "workspace": d.get("folder", {}).get("name") or "Shared Folder",
                                "dataset": query.get("model") or "Looker Explore"
                            })
                            break  # Avoid duplicates if multiple widgets reference the same table
        except Exception as e:
            logger.error(f"Error fetching Looker lineage: {e}")
        return lineage_map
