import uuid
import random
from datetime import datetime, timezone, timedelta
from backend.core.database import SessionLocal
from backend.modules.anomaly.models import SilverAnomalyFeature

def insert_mock_features() -> None:
    db = SessionLocal()
    try:
        tables = [
            ("bronze_financial_candles", ["symbol", "close_price", "volume", "candle_timestamp"]),
            ("bronze_fda_events", ["drug_name", "reaction_description", "serious", "receipt_date"]),
            ("bronze_github_events", ["event_id", "event_type", "repo_name", "created_at"]),
        ]
        
        now = datetime.now(timezone.utc)
        
        for table_name, cols in tables:
            print(f"Inserting mock features for {table_name}")
            for i in range(15):  # Insert 15 runs to have plenty of historical baseline data!
                run_time = now - timedelta(minutes=5 * (15 - i))
                
                null_rates = {col: max(0.0, random.gauss(0.5, 0.2)) for col in cols}
                row_count = int(random.gauss(100, 10))
                freshness = max(10.0, random.gauss(30.0, 5.0))
                
                mean_close = None
                tot_vol = None
                uniq_events = None
                
                if table_name == "bronze_financial_candles":
                    mean_close = random.gauss(150.0, 5.0)
                    tot_vol = int(random.gauss(10000, 1000))
                elif table_name == "bronze_github_events":
                    uniq_events = row_count
                    
                feature = SilverAnomalyFeature(
                    pipeline_run_id=uuid.uuid4(),
                    source_name=table_name,
                    row_count=row_count,
                    null_rates=null_rates,
                    mean_close_price=mean_close,
                    total_volume=tot_vol,
                    unique_events_count=uniq_events,
                    freshness_latency_seconds=freshness,
                    run_timestamp=run_time
                )
                db.add(feature)
        db.commit()
        print("Mock features inserted successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    insert_mock_features()
