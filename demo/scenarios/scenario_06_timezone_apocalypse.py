import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from backend.modules.ingestion.models import BronzeGithubEvent

logger = logging.getLogger("qolyx.demo.scenarios")

def inject(db: Session) -> dict:
    """Simulates a timezone shift scenario by shifting all GitHub event timestamps by +5h 30m."""
    logger.info("Injecting Scenario 06: Timezone Apocalypse")
    try:
        # Get existing GitHub event records
        existing_records = db.query(BronzeGithubEvent).all()
        
        if not existing_records:
            logger.error("No existing GitHub events found to shift timestamps. Skipping injection.")
            return {
                "scenario": "timezone_apocalypse",
                "description": "Failed to inject scenario: No existing GitHub events found in bronze_github_events table.",
                "affected_table": "bronze_github_events",
                "expected_trust_score_impact": {
                    "contract_penalty": 0,
                    "freshness_penalty": 0,
                    "volume_penalty": 0,
                    "anomaly_penalty": 0,
                    "dbt_penalty": 0
                }
            }

        updated_count = 0
        for record in existing_records:
            # Shift timestamps by +5 hours and 30 minutes
            if record.created_at:
                record.created_at = record.created_at + timedelta(hours=5, minutes=30)
            if record.ingested_at:
                record.ingested_at = record.ingested_at + timedelta(hours=5, minutes=30)
            updated_count += 1

        db.commit()
        logger.info(f"Successfully shifted timestamps (+5h 30m) for {updated_count} GitHub event records.")
        
    except Exception as exc:
        db.rollback()
        logger.error("Failed to inject Timezone Apocalypse scenario", exc_info=True)
        raise exc

    return {
        "scenario": "timezone_apocalypse",
        "description": "Simulates timezone deployment bug: all GitHub event timestamps shifted +5:30 hours (India timezone). Records now appear in tomorrow's date partition. Today shows 0 events. Daily aggregations completely broken. This exact bug has affected every global company at least once.",
        "affected_table": "bronze_github_events",
        "expected_trust_score_impact": {
            "contract_penalty": 10,
            "freshness_penalty": 0,
            "volume_penalty": 30,
            "anomaly_penalty": 0,
            "dbt_penalty": 0
        }
    }
