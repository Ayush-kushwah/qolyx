import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.core.events import redis_client

logger = logging.getLogger("qolyx.demo.scenarios")

def inject(db: Session) -> dict:
    """Simulates a finance close delay by updating Redis last_run to 6 hours ago."""
    logger.info("Injecting Scenario 04: Freshness Delay (Finance Close)")
    try:
        # Calculate timestamp 6 hours ago
        six_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        
        # Update Redis key
        redis_client.set("demo:freshness:last_run", six_hours_ago)
        logger.info(f"Successfully set demo:freshness:last_run Redis key to: {six_hours_ago}")
        
    except Exception as exc:
        logger.error("Failed to inject Freshness Delay scenario", exc_info=True)
        raise exc

    return {
        "scenario": "freshness_delay",
        "description": "Simulates finance close delay: pipeline intentionally skipped to trigger freshness SLA violation. Dataset has not updated in 6+ hours. CFO dashboard will show stale figures. This exact scenario caused a board meeting presentation failure at a Fortune 500 company.",
        "affected_table": "all_pipelines",
        "expected_trust_score_impact": {
            "contract_penalty": 0,
            "freshness_penalty": 30,
            "volume_penalty": 0,
            "anomaly_penalty": 0,
            "dbt_penalty": 0
        }
    }
