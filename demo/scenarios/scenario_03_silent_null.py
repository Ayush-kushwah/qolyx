import logging
from sqlalchemy.orm import Session
from backend.modules.ingestion.models import BronzeFdaEvent

logger = logging.getLogger("qolyx.demo.scenarios")

def inject(db: Session) -> dict:
    """Simulates silent null corruption by updating 40% of FDA event records to have serious=NULL."""
    logger.info("Injecting Scenario 03: Silent Null Corruption")
    try:
        # Get existing FDA adverse event records
        existing_records = db.query(BronzeFdaEvent).all()
        
        if not existing_records:
            logger.error("No existing FDA events found to corrupt. Skipping injection.")
            return {
                "scenario": "silent_null_corruption",
                "description": "Failed to inject scenario: No existing FDA events found in bronze_fda_events table.",
                "affected_table": "bronze_fda_events",
                "expected_trust_score_impact": {
                    "contract_penalty": 0,
                    "freshness_penalty": 0,
                    "volume_penalty": 0,
                    "anomaly_penalty": 0,
                    "dbt_penalty": 0
                }
            }

        total_records = len(existing_records)
        count_to_update = int(total_records * 0.40)
        # Ensure at least one record is updated if there are any records at all
        if count_to_update == 0 and total_records > 0:
            count_to_update = 1

        updated_count = 0
        for i in range(count_to_update):
            existing_records[i].serious = None
            updated_count += 1

        db.commit()
        logger.info(f"Successfully updated {updated_count} out of {total_records} FDA event records with serious=NULL.")
        
    except Exception as exc:
        db.rollback()
        logger.error("Failed to inject Silent Null Corruption scenario", exc_info=True)
        raise exc

    return {
        "scenario": "silent_null_corruption",
        "description": "Simulates silent null corruption: 40% of FDA serious field set to NULL after backend engineer made field optional. Severity classification model will make wrong predictions. This went undetected for 6 weeks at a real healthcare company.",
        "affected_table": "bronze_fda_events",
        "expected_trust_score_impact": {
            "contract_penalty": 30,
            "freshness_penalty": 0,
            "volume_penalty": 0,
            "anomaly_penalty": 15,
            "dbt_penalty": 0
        }
    }
