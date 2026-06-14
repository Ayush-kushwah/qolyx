from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BIConnector(ABC):
    """Abstract base class representing a generic BI Tool Connector."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Dry-run connectivity test to the target BI provider.

        Returns:
            True if connection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def fetch_workspaces(self) -> List[Dict[str, Any]]:
        """Fetch all workspaces/projects available on the target BI instance."""
        pass

    @abstractmethod
    def fetch_reports(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Fetch all reports/workbooks inside a specific workspace."""
        pass

    @abstractmethod
    def fetch_datasets(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Fetch all datasets/models available in a specific workspace."""
        pass

    @abstractmethod
    def fetch_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Fetch all tables/views mapped to a specific dataset."""
        pass

    @abstractmethod
    def fetch_columns(self, table_id: str) -> List[Dict[str, Any]]:
        """Fetch all columns and fields inside a target dataset table."""
        pass

    @abstractmethod
    def fetch_dashboards(self) -> List[Dict[str, Any]]:
        """Fetch all visual dashboards/pages currently deployed."""
        pass

    @abstractmethod
    def fetch_lineage(self, table_name: str) -> List[Dict[str, Any]]:
        """Traces lineage from visual dashboards and reports back to tables.

        Returns:
            List of dictionaries representing discovered dependency mappings.
        """
        pass
