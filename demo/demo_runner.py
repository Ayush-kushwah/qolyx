import os
import sys
import uuid
import subprocess
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.database import SessionLocal
from backend.main import seed_default_user
from demo.seed_data import seed_all_tables
from backend.modules.trust_score.service import TrustScoreService
from backend.modules.incidents.service import IncidentService
from backend.modules.incidents.models import Incident, IncidentTimeline, IncidentComment, IncidentRCA, AlertConfig
from backend.modules.trust_score.models import TrustScore
from backend.modules.ingestion.models import BronzeFinancialCandle, BronzeFdaEvent, BronzeGithubEvent
from demo.scenarios import (
    scenario_01_surge_pricing,
    scenario_02_api_breaking_change,
    scenario_03_silent_null,
    scenario_04_freshness_delay,
    scenario_05_duplicate_fraud,
    scenario_06_timezone_apocalypse,
)
from demo.demo_summary import print_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qolyx.demo.runner")

def run_dbt():
    """Runs dbt models programmatically using subprocess."""
    logger.info("Executing dbt run --models bronze+ ...")
    
    # Propagate DATABASE_URL parameters to DBT environment variables to prevent auth errors
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            parsed = urlparse(db_url)
            os.environ["DBT_USER"] = parsed.username or ""
            os.environ["DBT_PASSWORD"] = parsed.password or ""
            os.environ["DBT_HOST"] = parsed.hostname or ""
            os.environ["DBT_PORT"] = str(parsed.port or 5432)
            os.environ["DBT_DBNAME"] = parsed.path.lstrip("/")
            logger.info("Successfully propagated database credentials to dbt.")
        except Exception as e:
            logger.warning(f"Could not parse DATABASE_URL for dbt: {e}")

    try:
        subprocess.run(
            ["dbt", "deps", "--profiles-dir", "/app/dbt_project"],
            cwd="/app/dbt_project",
            check=True,
            capture_output=True,
            text=True
        )
        result = subprocess.run(
            ["dbt", "run", "--models", "bronze+", "--profiles-dir", "/app/dbt_project"],
            cwd="/app/dbt_project",
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("dbt run completed successfully.")
    except subprocess.CalledProcessError as err:
        logger.error(f"dbt command failed: {err.cmd}")
        if err.stdout:
            logger.error(f"Stdout:\n{err.stdout}")
        if err.stderr:
            logger.error(f"Stderr:\n{err.stderr}")
        raise err

def main():
    logger.info("Starting Qolyx Demo Setup...")
    db = SessionLocal()
    
    try:
        # Clean up database tables for the demo to ensure idempotency
        logger.info("Cleaning up existing database tables for a fresh run...")
        try:
            db.query(IncidentRCA).delete()
            db.query(IncidentComment).delete()
            db.query(IncidentTimeline).delete()
            db.query(Incident).delete()
            db.query(TrustScore).delete()
            db.query(BronzeFinancialCandle).delete()
            db.query(BronzeFdaEvent).delete()
            db.query(BronzeGithubEvent).delete()
            db.query(AlertConfig).delete()
            db.commit()
            logger.info("Database cleanup completed successfully.")
        except Exception as cleanup_err:
            db.rollback()
            logger.warning(f"Database cleanup failed (might be first run): {cleanup_err}")

        # Seed Alert Configurations from environment variables
        logger.info("Seeding Alert Configurations from environment variables...")
        try:
            slack_url = os.environ.get("SLACK_WEBHOOK_URL")
            if slack_url and "hooks.slack.com" in slack_url:
                db.add(AlertConfig(
                    id=uuid.uuid4(),
                    name="Slack Channel Alert",
                    channel_type="slack",
                    webhook_url=slack_url,
                    severity_threshold="LOW",
                    is_active=True
                ))

            discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
            if discord_url and "discord" in discord_url:
                db.add(AlertConfig(
                    id=uuid.uuid4(),
                    name="Discord Channel Alert",
                    channel_type="discord",
                    webhook_url=discord_url,
                    severity_threshold="LOW",
                    is_active=True
                ))

            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            telegram_chat = os.environ.get("TELEGRAM_CHAT_ID")
            if telegram_token and telegram_chat:
                db.add(AlertConfig(
                    id=uuid.uuid4(),
                    name="Telegram Bot Alert",
                    channel_type="telegram",
                    telegram_bot_token=telegram_token,
                    telegram_chat_id=telegram_chat,
                    severity_threshold="LOW",
                    is_active=True
                ))

            smtp_host = os.environ.get("SMTP_HOST") or "qolyx-mail"
            smtp_port_val = os.environ.get("SMTP_PORT") or "1025"
            db.add(AlertConfig(
                id=uuid.uuid4(),
                name="SMTP Email Alert",
                channel_type="email",
                email_config={
                    "smtp_server": smtp_host,
                    "smtp_port": int(smtp_port_val),
                    "smtp_user": os.environ.get("SMTP_USER"),
                    "smtp_password": os.environ.get("SMTP_PASSWORD"),
                    "from_address": os.environ.get("ALERT_EMAIL_FROM") or "alerts@qolyx.io",
                    "to_addresses": os.environ.get("ALERT_EMAIL_TO") or "oncall@qolyx.io"
                },
                severity_threshold="LOW",
                is_active=True
            ))

            db.commit()
            logger.info("Successfully seeded Alert Configurations.")
        except Exception as seed_err:
            db.rollback()
            logger.error(f"Failed to seed Alert Configurations: {seed_err}")

        # 1. Seed Admin User
        seed_default_user()
        
        # 2. Seed Initial Demo Data
        logger.info("Seeding initial data for 3 pipelines...")
        run_id = uuid.uuid4()
        seed_all_tables(db, run_id)
        
        # 3. Run dbt models first time to build silver and gold tables
        run_dbt()
        
        # 4. Calculate and Save Initial Healthy Trust Scores (100)
        logger.info("Calculating initial healthy trust scores...")
        tables = [
            "bronze_financial_candles",
            "bronze_fda_events",
            "bronze_github_events",
            "gold_daily_market_summary",
            "gold_fda_severity_stats",
            "gold_github_activity_summary"
        ]
        
        for table in tables:
            penalties = {
                "contract_penalty": 0,
                "anomaly_penalty": 0,
                "dbt_penalty": 0,
                "freshness_penalty": 0,
                "volume_penalty": 0
            }
            score, total_penalty, status = TrustScoreService.calculate_trust_score(penalties)
            TrustScoreService.save_trust_score(db, run_id, table, penalties, score, total_penalty, status)
            
        logger.info("Initial healthy trust scores saved (100 for all tables).")
        
        # 5. Execute 6 Failure Scenarios in Sequence
        
        # Scenario 1: Volume Spike
        logger.info("Executing Scenario 1: Volume Spike...")
        scenario_01_surge_pricing.inject(db)
        run_dbt()
        s1_penalties = {
            "contract_penalty": 0,
            "anomaly_penalty": 0,
            "dbt_penalty": 0,
            "freshness_penalty": 0,
            "volume_penalty": 20
        }
        score, total_penalty, status = TrustScoreService.calculate_trust_score(s1_penalties)
        ts_rec = TrustScoreService.save_trust_score(db, run_id, "bronze_financial_candles", s1_penalties, score, total_penalty, status)
        incident_s1 = Incident(
            id=uuid.uuid4(),
            trust_score_id=ts_rec.id,
            pipeline_run_id=run_id,
            table_name="bronze_financial_candles",
            severity="HIGH",
            state="OPEN",
            title="Volume anomaly detected on bronze_financial_candles",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(incident_s1)
        db.commit()
        
        # Scenario 2: Schema Drift
        logger.info("Executing Scenario 2: Schema Drift...")
        scenario_02_api_breaking_change.inject(db)
        run_dbt()
        s2_penalties = {
            "contract_penalty": 35,
            "anomaly_penalty": 0,
            "dbt_penalty": 0,
            "freshness_penalty": 0,
            "volume_penalty": 0
        }
        score, total_penalty, status = TrustScoreService.calculate_trust_score(s2_penalties)
        ts_rec = TrustScoreService.save_trust_score(db, run_id, "bronze_financial_candles", s2_penalties, score, total_penalty, status)
        db.expire_all()
        inc_s2 = db.query(Incident).filter(Incident.pipeline_run_id == run_id, Incident.table_name == "bronze_financial_candles", Incident.severity != "HIGH").first()
        if inc_s2:
            inc_s2.title = "Schema drift detected on bronze_financial_candles"
            inc_s2.severity = "CRITICAL"
            db.commit()
            
        # Scenario 3: Null Corruption
        logger.info("Executing Scenario 3: Null Corruption...")
        scenario_03_silent_null.inject(db)
        run_dbt()
        s3_penalties = {
            "contract_penalty": 30,
            "anomaly_penalty": 20,
            "dbt_penalty": 0,
            "freshness_penalty": 0,
            "volume_penalty": 0
        }
        score, total_penalty, status = TrustScoreService.calculate_trust_score(s3_penalties)
        ts_rec = TrustScoreService.save_trust_score(db, run_id, "bronze_fda_events", s3_penalties, score, total_penalty, status)
        
        # Scenario 4: Freshness Delay
        logger.info("Executing Scenario 4: Freshness Delay...")
        scenario_04_freshness_delay.inject(db)
        run_dbt()
        s4_penalties = {
            "contract_penalty": 30,
            "anomaly_penalty": 20,
            "dbt_penalty": 0,
            "freshness_penalty": 10,
            "volume_penalty": 0
        }
        score, total_penalty, status = TrustScoreService.calculate_trust_score(s4_penalties)
        ts_rec = TrustScoreService.save_trust_score(db, run_id, "bronze_fda_events", s4_penalties, score, total_penalty, status)
        db.expire_all()
        inc_s4 = db.query(Incident).filter(Incident.pipeline_run_id == run_id, Incident.table_name == "bronze_fda_events").first()
        if inc_s4:
            inc_s4.title = "Freshness SLA violated on bronze_fda_events"
            inc_s4.severity = "MEDIUM"
            db.commit()
            
        # Scenario 5: Duplicate Fraud
        logger.info("Executing Scenario 5: Duplicate Fraud...")
        scenario_05_duplicate_fraud.inject(db)
        run_dbt()
        s5_penalties = {
            "contract_penalty": 30,
            "anomaly_penalty": 20,
            "dbt_penalty": 20,
            "freshness_penalty": 0,
            "volume_penalty": 0
        }
        score, total_penalty, status = TrustScoreService.calculate_trust_score(s5_penalties)
        ts_rec = TrustScoreService.save_trust_score(db, run_id, "bronze_financial_candles", s5_penalties, score, total_penalty, status)
        
        # Scenario 6: Timezone Apocalypse
        logger.info("Executing Scenario 6: Timezone Apocalypse...")
        scenario_06_timezone_apocalypse.inject(db)
        run_dbt()
        s6_penalties = {
            "contract_penalty": 30,
            "anomaly_penalty": 20,
            "dbt_penalty": 20,
            "freshness_penalty": 0,
            "volume_penalty": 10
        }
        score, total_penalty, status = TrustScoreService.calculate_trust_score(s6_penalties)
        ts_rec = TrustScoreService.save_trust_score(db, run_id, "bronze_github_events", s6_penalties, score, total_penalty, status)
        
        logger.info("All scenarios successfully executed and Trust Scores updated.")
        
    except Exception as exc:
        db.rollback()
        logger.critical("Demo runner failed to execute", exc_info=True)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
