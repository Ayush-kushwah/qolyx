import logging
import uuid
from sqlalchemy.orm import Session
from backend.modules.ingestion.models import BronzeFinancialCandle

logger = logging.getLogger("qolyx.demo.scenarios")

def inject(db: Session) -> dict:
    """Simulates payment processor retry bug by duplicating all existing BronzeFinancialCandle records exactly."""
    logger.info("Injecting Scenario 05: Duplicate Fraud")
    try:
        # Get existing financial candle records
        existing_records = db.query(BronzeFinancialCandle).all()
        
        if not existing_records:
            logger.error("No existing financial candles found to duplicate. Skipping injection.")
            return {
                "scenario": "duplicate_fraud",
                "description": "Failed to inject scenario: No existing financial candles found in bronze_financial_candles table.",
                "affected_table": "bronze_financial_candles",
                "expected_trust_score_impact": {
                    "contract_penalty": 0,
                    "freshness_penalty": 0,
                    "volume_penalty": 0,
                    "anomaly_penalty": 0,
                    "dbt_penalty": 0
                }
            }

        duplicated_count = 0
        for record in existing_records:
            new_record = BronzeFinancialCandle(
                id=uuid.uuid4(),  # New UUID for the primary key
                pipeline_run_id=record.pipeline_run_id,  # Reused to cause duplicate validation failures
                symbol=record.symbol,
                open_price=record.open_price,
                high_price=record.high_price,
                low_price=record.low_price,
                close_price=record.close_price,
                volume=record.volume,
                candle_timestamp=record.candle_timestamp,
                ingested_at=record.ingested_at
            )
            db.add(new_record)
            duplicated_count += 1

        db.commit()
        logger.info(f"Successfully duplicated {duplicated_count} BronzeFinancialCandle records.")
        
    except Exception as exc:
        db.rollback()
        logger.error("Failed to inject Duplicate Fraud scenario", exc_info=True)
        raise exc

    return {
        "scenario": "duplicate_fraud",
        "description": "Simulates payment processor retry bug: all financial candle records duplicated exactly. Row count doubled. Revenue aggregations inflated by 100%. dbt uniqueness tests will fail on pipeline_run_id. This caused a company to file incorrect quarterly earnings.",
        "affected_table": "bronze_financial_candles",
        "expected_trust_score_impact": {
            "contract_penalty": 0,
            "freshness_penalty": 0,
            "volume_penalty": 20,
            "anomaly_penalty": 0,
            "dbt_penalty": 14
        }
    }
