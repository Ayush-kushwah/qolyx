import logging
import uuid
from sqlalchemy.orm import Session
from backend.modules.ingestion.models import BronzeFinancialCandle

logger = logging.getLogger("qolyx.demo.scenarios")

def inject(db: Session) -> dict:
    """Simulates a volume spike scenario by multiplying existing AAPL records by 10x."""
    logger.info("Injecting Scenario 01: Surge Pricing (Volume Spike)")
    try:
        # Query existing AAPL candles
        aapl_records = db.query(BronzeFinancialCandle).filter(BronzeFinancialCandle.symbol == "AAPL").all()
        
        if not aapl_records:
            logger.error("No existing AAPL records found to duplicate. Skipping injection.")
            return {
                "scenario": "surge_pricing",
                "description": "Failed to inject scenario: No existing AAPL records found.",
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
        # Duplicate each record 10 times
        for record in aapl_records:
            for _ in range(10):
                new_record = BronzeFinancialCandle(
                    pipeline_run_id=uuid.uuid4(),  # Issue 1: New UUID for each record
                    symbol=record.symbol,
                    open_price=record.open_price,
                    high_price=record.high_price,
                    low_price=record.low_price,
                    close_price=record.close_price,
                    volume=record.volume,
                    candle_timestamp=record.candle_timestamp  # Issue 3: Same timestamp as original
                )
                db.add(new_record)
                duplicated_count += 1

        db.commit()
        logger.info(f"Successfully duplicated AAPL records. Inserted {duplicated_count} records.")
        
    except Exception as exc:
        db.rollback()
        logger.error("Failed to inject Surge Pricing scenario", exc_info=True)
        raise exc

    return {
        "scenario": "surge_pricing",
        "description": "Simulates Uber-style volume spike: AAPL candle records multiplied 10x simulating market data feed duplication during peak hours. Revenue aggregations downstream will be inflated.",
        "affected_table": "bronze_financial_candles",
        "expected_trust_score_impact": {
            "contract_penalty": 0,
            "freshness_penalty": 0,
            "volume_penalty": 30,
            "anomaly_penalty": 0,
            "dbt_penalty": 0
        }
    }
