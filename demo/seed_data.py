import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.modules.ingestion.models import BronzeFinancialCandle, BronzeFdaEvent, BronzeGithubEvent

def seed_financial_candles(db: Session, pipeline_run_id: uuid.UUID, num_rows: int = 500):
    """Seeds the bronze_financial_candles table with deterministic synthetic data."""
    symbols = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
    price_ranges = {
        "AAPL": (150.0, 220.0),
        "MSFT": (300.0, 450.0),
        "TSLA": (170.0, 280.0),
        "GOOGL": (130.0, 180.0),
        "AMZN": (120.0, 200.0),
    }
    
    random.seed(42)  # For reproducibility
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=30)
    
    # Calculate interval to distribute rows evenly across 30 days
    rows_per_symbol = num_rows // len(symbols)
    interval = timedelta(days=30) / rows_per_symbol

    for symbol in symbols:
        min_p, max_p = price_ranges[symbol]
        for i in range(rows_per_symbol):
            candle_timestamp = start_date + (i * interval)
            
            open_price = round(random.uniform(min_p, max_p), 2)
            close_price = round(random.uniform(min_p, max_p), 2)
            high_price = round(max(open_price, close_price) + random.uniform(0, (max_p - min_p) * 0.02), 2)
            low_price = round(min(open_price, close_price) - random.uniform(0, (max_p - min_p) * 0.02), 2)
            
            # Ensure within bounds
            high_price = min(high_price, max_p)
            low_price = max(low_price, min_p)
            
            volume = random.randint(1000, 100000)
            
            candle = BronzeFinancialCandle(
                id=uuid.uuid4(),
                pipeline_run_id=pipeline_run_id,
                symbol=symbol,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                candle_timestamp=candle_timestamp,
                ingested_at=now
            )
            db.add(candle)
    
    db.commit()

def seed_fda_events(db: Session, pipeline_run_id: uuid.UUID, num_rows: int = 300):
    """Seeds the bronze_fda_events table with deterministic synthetic data."""
    drugs = ["Aspirin", "Ibuprofen", "Paracetamol", "Metformin", "Lisinopril"]
    reactions = ["Headache", "Nausea", "Rash", "Dizziness", "Fatigue"]
    countries = ["US", "CA", "GB", "DE", "FR"]
    
    random.seed(42)  # For reproducibility
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=30)
    interval = timedelta(days=30) / num_rows

    for i in range(num_rows):
        event_date = start_date + (i * interval)
        receipt_date = event_date.strftime("%Y%m%d")
        
        serious = random.choice(["1", "2", None])
        reporter_country = random.choice(countries)
        drug_name = random.choice(drugs)
        reaction_description = random.choice(reactions)
        seriousness_hospitalization = random.choice(["1", "2", None])
        
        raw_payload = {
            "receiptdate": receipt_date,
            "seriousness": serious,
            "reportercountry": reporter_country,
            "patient": {
                "drug": [{"medicinalproduct": drug_name}],
                "reaction": [{"reactionmeddrapt": reaction_description}]
            },
            "seriousnesshospitalization": seriousness_hospitalization
        }
        
        event = BronzeFdaEvent(
            id=uuid.uuid4(),
            pipeline_run_id=pipeline_run_id,
            receipt_date=receipt_date,
            serious=serious,
            reporter_country=reporter_country,
            drug_name=drug_name,
            reaction_description=reaction_description,
            seriousness_hospitalization=seriousness_hospitalization,
            raw_payload=raw_payload,
            ingested_at=now
        )
        db.add(event)
        
    db.commit()

def seed_github_events(db: Session, pipeline_run_id: uuid.UUID, num_rows: int = 200):
    """Seeds the bronze_github_events table with deterministic synthetic data."""
    event_types = ["PushEvent", "PullRequestEvent", "IssuesEvent", "IssueCommentEvent", "WatchEvent"]
    actors = ["octocat", "coder123", "bughunter", "devgirl", "securitybot"]
    repos = ["octocat/HelloWorld", "coder123/awesome-project", "bughunter/patch-fix"]
    
    random.seed(42)  # For reproducibility
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=30)
    interval = timedelta(days=30) / num_rows

    for i in range(num_rows):
        created_at = start_date + (i * interval)
        event_id = str(1000000000 + i)
        event_type = random.choice(event_types)
        actor_login = random.choice(actors)
        repo_name = random.choice(repos)
        payload_action = random.choice(["created", "opened", "closed", None])
        
        raw_payload = {
            "id": event_id,
            "type": event_type,
            "actor": {"login": actor_login},
            "repo": {"name": repo_name},
            "payload": {"action": payload_action}
        }
        
        event = BronzeGithubEvent(
            id=uuid.uuid4(),
            pipeline_run_id=pipeline_run_id,
            event_id=event_id,
            event_type=event_type,
            actor_login=actor_login,
            repo_name=repo_name,
            payload_action=payload_action,
            created_at=created_at,
            raw_payload=raw_payload,
            ingested_at=now
        )
        db.add(event)
        
    db.commit()

def seed_all_tables(db: Session, pipeline_run_id: uuid.UUID = None):
    """Seeds all three bronze tables with deterministic data."""
    if not pipeline_run_id:
        pipeline_run_id = uuid.uuid4()
        
    seed_financial_candles(db, pipeline_run_id, num_rows=500)
    seed_fda_events(db, pipeline_run_id, num_rows=300)
    seed_github_events(db, pipeline_run_id, num_rows=200)
