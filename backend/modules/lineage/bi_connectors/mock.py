import logging
from typing import Any, Dict, List
from backend.modules.lineage.bi_connectors.base import BIConnector

logger = logging.getLogger("qolyx.lineage.bi_connectors.mock")


class MockBIConnector(BIConnector):
    """Mock BI Connector for demo environments.

    Automatically binds downstream dashboards to Gold tables when no integrations are configured.
    """

    def test_connection(self) -> bool:
        return True

    def fetch_workspaces(self) -> List[Dict[str, Any]]:
        return [
            {"id": "ws_finance", "name": "Financial Analytics"},
            {"id": "ws_compliance", "name": "FDA & Compliance Reports"}
        ]

    def fetch_reports(self, workspace_id: str) -> List[Dict[str, Any]]:
        if workspace_id == "ws_finance":
            return [{
                "id": "rep_market_trends",
                "name": "Market Trend Summary Workbook",
                "datasetId": "ds_market"
            }]
        elif workspace_id == "ws_compliance":
            return [{
                "id": "rep_fda_compliance",
                "name": "FDA Severity Analysis Report",
                "datasetId": "ds_fda"
            }]
        return []

    def fetch_datasets(self, workspace_id: str) -> List[Dict[str, Any]]:
        if workspace_id == "ws_finance":
            return [{"id": "ds_market", "name": "Market Daily Summary Model"}]
        elif workspace_id == "ws_compliance":
            return [{"id": "ds_fda", "name": "FDA Event Severity Aggregates"}]
        return []

    def fetch_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        if dataset_id == "ds_market":
            return [{"name": "gold_daily_market_summary"}]
        elif dataset_id == "ds_fda":
            return [{"name": "gold_fda_severity_stats"}]
        return []

    def fetch_columns(self, table_id: str) -> List[Dict[str, Any]]:
        if table_id == "gold_daily_market_summary":
            return [
                {"name": "avg_close_price"},
                {"name": "total_volume"},
                {"name": "symbol"}
            ]
        elif table_id == "gold_fda_severity_stats":
            return [
                {"name": "event_count"},
                {"name": "serious_count"},
                {"name": "report_date"}
            ]
        return []

    def fetch_dashboards(self) -> List[Dict[str, Any]]:
        return [
            {"id": "market_kpis", "name": "Executive Market Summary Dashboard (Tableau)"},
            {"id": "fda_dashboard", "name": "FDA Adverse Event Severity Dashboard (Looker)"}
        ]

    def fetch_lineage(self, table_name: str) -> List[Dict[str, Any]]:
        lineage_map = []
        name_lower = table_name.lower()
        
        if "gold_daily_market_summary" in name_lower:
            lineage_map.append({
                "dashboard_id": "dashboard.tableau.market_executive_kpis",
                "dashboard_name": "Executive Market Summary Dashboard (Tableau)",
                "workspace": "Financial Analytics",
                "dataset": "Market Daily Summary Model"
            })
        elif "gold_fda_severity_stats" in name_lower:
            lineage_map.append({
                "dashboard_id": "dashboard.looker.fda_severity_analytics",
                "dashboard_name": "FDA Adverse Event Severity Dashboard (Looker)",
                "workspace": "FDA & Compliance Reports",
                "dataset": "FDA Event Severity Aggregates"
            })
            
        return lineage_map
