import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.modules.ingestion.models import BronzeFinancialCandle

logger = logging.getLogger("qolyx.demo.scenarios")

def inject(db: Session) -> dict:
    """Simulates an API breaking change where close_price is completely omitted from insert."""
    logger.info("Injecting Scenario 02: API Breaking Change")
    try:
        # Get existing real records to copy
        existing_records = db.query(BronzeFinancialCandle).limit(5).all()
        
        if not existing_records:
            logger.error("No existing records found to copy. Cannot inject API breaking change scenario.")
            return {
                "scenario": "api_breaking_change",
                "description": "Failed: No existing records to copy. Run ingestion DAGs first.",
                "affected_table": "bronze_financial_candles",
                "expected_trust_score_impact": {
                    "contract_penalty": 0,
                    "freshness_penalty": 0,
                    "volume_penalty": 0,
                    "anomaly_penalty": 0,
                    "dbt_penalty": 0
                }
            }

        inserted_count = 0
        for record in existing_records:
            new_record = BronzeFinancialCandle(
                pipeline_run_id=uuid.uuid4(),  # New UUID per record
                symbol=record.symbol,
                open_price=record.open_price,
                high_price=record.high_price,
                low_price=record.low_price,
                # close_price is intentionally omitted
                volume=record.volume,
                candle_timestamp=record.candle_timestamp,
                ingested_at=datetime.now(timezone.utc)
            )
            db.add(new_record)
            inserted_count += 1

        db.commit()
        logger.info(f"Successfully inserted {inserted_count} records with close_price omitted.")
        
    except Exception as exc:
        db.rollback()
        logger.error("Failed to inject API Breaking Change scenario", exc_info=True)
        raise exc

    return {
        "scenario": "api_breaking_change",
        "description": "Simulates Salesforce API breaking change: close_price column is COMPLETELY MISSING from ingested payload because upstream renamed it to closing_value. Pipeline continues running successfully but key financial metric is absent. Dashboards will show $0 revenue. This exact incident cost a company 3 days of incorrect reporting before detection.",
        "affected_table": "bronze_financial_candles",
        "expected_trust_score_impact": {
            "contract_penalty": 40,
            "freshness_penalty": 0,
            "volume_penalty": 0,
            "anomaly_penalty": 0,
            "dbt_penalty": 0
        }
    }
