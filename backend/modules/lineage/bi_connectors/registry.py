import os
import json
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

# Import connectors
from backend.core.config import settings as app_settings
from backend.modules.users.models import IntegrationConnection
from backend.modules.users.utils import decrypt_config
from backend.modules.lineage.bi_connectors.base import BIConnector
from backend.modules.lineage.bi_connectors.powerbi import PowerBIConnector
from backend.modules.lineage.bi_connectors.tableau import TableauConnector
from backend.modules.lineage.bi_connectors.looker import LookerConnector
from backend.modules.lineage.bi_connectors.mock import MockBIConnector

logger = logging.getLogger("qolyx.lineage.bi_connectors.registry")


def get_connector(connector_type: str, db: Session) -> BIConnector:
    """Resolves and instantiates the target BI connector from database settings.

    Falls back to MockBIConnector if no active configurations exist.
    """
    prov_upper = connector_type.upper()
    
    # 1. Look for active connection in IntegrationConnection database
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.provider == prov_upper,
        IntegrationConnection.is_active == True
    ).first()
    
    if conn:
        try:
            # Decrypt configuration parameters
            decrypted = decrypt_config(conn.encrypted_config, app_settings.SECRET_KEY.get_secret_value())
            config = json.loads(decrypted)
            
            if prov_upper == "POWERBI":
                return PowerBIConnector(
                    tenant_id=config.get("tenant_id", app_settings.POWER_BI_TENANT_ID),
                    client_id=config.get("client_id", app_settings.POWER_BI_CLIENT_ID),
                    client_secret=config.get("client_secret", app_settings.POWER_BI_CLIENT_SECRET),
                    limit_per_hour=app_settings.POWER_BI_RATE_LIMIT_PER_HOUR
                )
            elif prov_upper == "TABLEAU":
                return TableauConnector(
                    server_url=config.get("url", app_settings.TABLEAU_SERVER_URL),
                    access_token=config.get("token", app_settings.TABLEAU_PERSONAL_ACCESS_TOKEN),
                    token_name=config.get("token_name", "qolyx_token"),
                    site_name=config.get("site_name", "")
                )
            elif prov_upper == "LOOKER":
                return LookerConnector(
                    host=config.get("url", app_settings.LOOKER_HOST),
                    client_id=config.get("client_id", app_settings.LOOKER_CLIENT_ID),
                    client_secret=config.get("client_secret", app_settings.LOOKER_CLIENT_SECRET)
                )
        except Exception as e:
            logger.error(f"Failed to instantiate configured connector '{connector_type}': {e}. Falling back to Mock.", exc_info=True)
            
    # 2. Check fallback environment variables directly
    try:
        if prov_upper == "POWERBI" and app_settings.POWER_BI_CLIENT_ID:
            return PowerBIConnector(
                tenant_id=app_settings.POWER_BI_TENANT_ID,
                client_id=app_settings.POWER_BI_CLIENT_ID,
                client_secret=app_settings.POWER_BI_CLIENT_SECRET,
                limit_per_hour=app_settings.POWER_BI_RATE_LIMIT_PER_HOUR
            )
        elif prov_upper == "TABLEAU" and app_settings.TABLEAU_SERVER_URL:
            return TableauConnector(
                server_url=app_settings.TABLEAU_SERVER_URL,
                access_token=app_settings.TABLEAU_PERSONAL_ACCESS_TOKEN
            )
        elif prov_upper == "LOOKER" and app_settings.LOOKER_HOST:
            return LookerConnector(
                host=app_settings.LOOKER_HOST,
                client_id=app_settings.LOOKER_CLIENT_ID,
                client_secret=app_settings.LOOKER_CLIENT_SECRET
            )
    except Exception as e:
        logger.error(f"Failed loading environment variables for connector '{connector_type}': {e}")

    logger.debug(f"No credentials found for '{connector_type}'. Falling back to MockBIConnector.")
    return MockBIConnector()


def get_all_active_connectors(db: Session) -> List[BIConnector]:
    """Retrieves all active connectors based on settings.

    Returns:
        List containing active connectors, defaulting to MockBIConnector if empty.
    """
    connectors: List[BIConnector] = []
    
    # Check all provider options
    for prov in ["POWERBI", "TABLEAU", "LOOKER"]:
        conn = get_connector(prov, db)
        if not isinstance(conn, MockBIConnector):
            connectors.append(conn)
            
    if not connectors:
        connectors.append(MockBIConnector())
        
    return connectors
