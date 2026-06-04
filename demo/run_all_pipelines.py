import asyncio
import uuid
import sys
import os
import traceback
from datetime import datetime, timezone

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.database import SessionLocal
from backend.modules.contracts.models import Contract
from backend.modules.ingestion.services import IngestionService
from backend.modules.incidents.models import Incident, IncidentRCA, IncidentTimeline
from backend.modules.trust_score.models import TrustScore

async def run_pipeline_test(source_name, table_name):
    print(f"\n==================================================")
    print(f"Testing Ingestion Pipeline: {source_name} ({table_name})")
    print(f"==================================================")
    
    db = SessionLocal()
    try:
        # 1. Seed or update contract to be empty {} to trigger contract violations (extra columns)
        contract = db.query(Contract).filter(Contract.table_name == table_name).first()
        if not contract:
            print(f"Creating contract for {table_name}...")
            contract = Contract(
                id=uuid.uuid4(),
                name=f"Contract {table_name}",
                table_name=table_name,
                version=1,
                schema_definition={},
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(contract)
        else:
            print(f"Contract for {table_name} already exists. Setting schema_definition to empty dict.")
            contract.schema_definition = {}
        db.commit()

        # 2. Run ingestion
        print(f"Triggering ingestion for {source_name}...")
        pipeline_run_id = await IngestionService.run_ingestion(db, source_name)
        print(f"Ingestion run completed successfully. Run ID: {pipeline_run_id}")
        
        # 3. Check TrustScore
        db.expire_all()
        trust_score = db.query(TrustScore).filter(TrustScore.pipeline_run_id == pipeline_run_id).first()
        if trust_score:
            print(f"Trust Score Calculated: {trust_score.trust_score} (Status: {trust_score.trust_score_status})")
            print(f"Penalty Breakdown: {trust_score.breakdown}")
        else:
            print("ERROR: No TrustScore found for this run!")
            return

        # 4. Check Incident
        incident = db.query(Incident).filter(Incident.pipeline_run_id == pipeline_run_id).first()
        if incident:
            print(f"Incident Created: YES (ID: {incident.id}, Title: {incident.title})")
            
            # 5. Check RCA
            rca = db.query(IncidentRCA).filter(IncidentRCA.incident_id == incident.id).first()
            if rca:
                print(f"RCA Auto-Generated: YES")
                print(f"RCA Summary: {rca.summary}")
                print(f"RCA Root Cause: {rca.root_cause}")
                print(f"RCA Recommendation: {rca.recommendation}")
            else:
                print("RCA Auto-Generated: NO (Verification Failed)")
                
            # 6. Check Timeline Alerts
            timeline_alerts = db.query(IncidentTimeline).filter(
                IncidentTimeline.incident_id == incident.id,
                IncidentTimeline.event_type == "ALERT_DISPATCHED"
            ).all()
            if timeline_alerts:
                print(f"Alerts Dispatched: YES (Channels: {timeline_alerts[0].event_data.get('channels')})")
            else:
                print("Alerts Dispatched: NO (Verification Failed)")
        else:
            print("Incident Created: NO (Verification Failed - trust score under 70 must trigger incident)")
            
    except Exception as e:
        print(f"Ingestion run failed for {source_name}: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

async def main():
    # Run all three pipelines, using separate sessions
    await run_pipeline_test("finnhub", "bronze_financial_candles")
    await run_pipeline_test("fda", "bronze_fda_events")
    await run_pipeline_test("github", "bronze_github_events")

if __name__ == "__main__":
    asyncio.run(main())
