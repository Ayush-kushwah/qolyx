import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import text, desc
from sqlalchemy.orm import Session

from backend.modules.incidents.models import Incident, IncidentRCA, IncidentTimeline
from backend.modules.trust_score.models import TrustScore

logger = logging.getLogger("qolyx.incidents.rca")


class RCAService:
    """Service to generate and manage deterministic Root Cause Analysis (RCA) records for incidents."""

    @staticmethod
    def get_downstream_impact(db: Session, table_name: str) -> List[str]:
        """Query dbt lineage to find downstream tables.
        
        For Phase 8, return placeholder list with common gold tables.
        Phase 9 will enhance with OpenLineage.
        """
        # Placeholder for Phase 8
        downstream_map = {
            "bronze_financial_candles": ["gold_daily_market_summary"],
            "bronze_fda_events": ["gold_fda_severity_stats"],
            "bronze_github_events": ["gold_github_activity_summary"],
        }
        return downstream_map.get(table_name, [])

    @staticmethod
    def generate_contributing_factors(trust_score: TrustScore, primary_driver: str) -> List[str]:
        """Helper to extract contributing factors (non-primary penalties with deduction > 0)."""
        penalties = trust_score.breakdown
        contributing_factors = []
        for key, val in penalties.items():
            driver_name = key.replace("_penalty", "")
            if driver_name != primary_driver and val > 0:
                contributing_factors.append(f"{driver_name.capitalize()} penalty (-{val})")
        return contributing_factors

    @staticmethod
    def generate_recommendation(primary_penalty: str, table_name: str) -> str:
        """Helper to generate standard developer recommendations based on the primary penalty driver."""
        recommendations = {
            "contract": f"Verify the schema and nullability constraints of incoming records for table '{table_name}'. Update contract definitions if schema changes are intentional.",
            "volume": f"Verify if upstream database queries executed correctly or if source dataset extraction was incomplete for table '{table_name}'.",
            "freshness": f"Check Airflow scheduler logs, network connectivity to data sources, or upstream pipeline latency for table '{table_name}'.",
            "anomaly": f"Investigate the feature distribution drift and SHAP explainability values in the anomaly detection logs for table '{table_name}'.",
            "dbt": f"Review the dbt test execution logs for table '{table_name}'. Check for uniqueness, nullity, or custom schema violations."
        }
        return recommendations.get(
            primary_penalty,
            f"Review the pipeline run logs, active data profiling results, and metrics dashboards for table '{table_name}'."
        )

    @staticmethod
    def generate_rca(db: Session, incident_id: uuid.UUID) -> IncidentRCA:
        """Generates a new version of deterministic Root Cause Analysis (RCA) for an incident."""
        logger.info(f"Generating RCA for incident: {incident_id}")

        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident with ID {incident_id} does not exist.")

        # Lookup trust score using pipeline_run_id (or trust_score_id)
        trust_score = db.query(TrustScore).filter(
            TrustScore.pipeline_run_id == incident.pipeline_run_id
        ).first()

        if not trust_score:
            logger.warning(
                "No TrustScore found for incident's pipeline run. Creating fallback RCA.",
                extra={"incident_id": str(incident_id), "pipeline_run_id": str(incident.pipeline_run_id)}
            )
            return RCAService._create_fallback_rca(db, incident)

        # Retrieve penalty breakdown
        penalties = {
            "contract": trust_score.contract_penalty or 0,
            "freshness": trust_score.freshness_penalty or 0,
            "volume": trust_score.volume_penalty or 0,
            "anomaly": trust_score.anomaly_penalty or 0,
            "dbt": trust_score.dbt_penalty or 0,
        }

        # Find the primary penalty driver (largest deduction)
        primary_driver = max(penalties, key=penalties.get)
        primary_val = penalties[primary_driver]

        if primary_val == 0:
            logger.info("All penalties are 0. Generating fallback generic RCA.")
            return RCAService._create_fallback_rca(db, incident)

        summary = ""
        root_cause = ""
        confidence = 1.0

        # Fetch actual metrics where applicable
        if primary_driver == "contract":
            try:
                from backend.modules.contracts.models import ContractViolation
                violations = db.query(ContractViolation).filter(
                    ContractViolation.pipeline_run_id == incident.pipeline_run_id
                ).all()
                violations_count = len(violations)
                violating_cols = list({v.column_name for v in violations if v.column_name})
                
                cols_str = ", ".join(violating_cols) if violating_cols else "unknown columns"
                summary = f"Dataset contract validation failed on table '{incident.table_name}'."
                root_cause = f"Ingested data had {violations_count} contract violation(s) on column(s): {cols_str}."
            except Exception as e:
                logger.warning(f"Error querying contract violations: {e}")
                summary = f"Dataset contract validation failed on table '{incident.table_name}'."
                root_cause = "Contract violations occurred during ingestion."
                confidence = 0.8

        elif primary_driver == "volume":
            try:
                from backend.modules.anomaly.models import SilverAnomalyFeature, AnomalyBaseline
                feature = db.query(SilverAnomalyFeature).filter(
                    SilverAnomalyFeature.pipeline_run_id == incident.pipeline_run_id
                ).first()
                baseline = db.query(AnomalyBaseline).filter(
                    AnomalyBaseline.table_name == incident.table_name,
                    AnomalyBaseline.metric_name == "row_count"
                ).first()

                actual_val = feature.row_count if feature else None
                baseline_val = baseline.mean if baseline else None

                summary = f"Ingestion volume anomaly detected on table '{incident.table_name}'."
                if actual_val is not None and baseline_val is not None:
                    root_cause = f"The actual row count of {actual_val} deviated significantly from the historical baseline of {baseline_val:.1f} rows."
                else:
                    root_cause = "The ingested row count deviated from baseline volume expectations."
            except Exception as e:
                logger.warning(f"Error querying volume features: {e}")
                summary = f"Ingestion volume anomaly detected on table '{incident.table_name}'."
                root_cause = "The ingested volume deviated from baseline expectations."
                confidence = 0.8

        elif primary_driver == "freshness":
            try:
                from backend.modules.anomaly.models import SilverAnomalyFeature, AnomalyBaseline
                feature = db.query(SilverAnomalyFeature).filter(
                    SilverAnomalyFeature.pipeline_run_id == incident.pipeline_run_id
                ).first()
                baseline = db.query(AnomalyBaseline).filter(
                    AnomalyBaseline.table_name == incident.table_name,
                    AnomalyBaseline.metric_name == "freshness_latency_seconds"
                ).first()

                actual_val = feature.freshness_latency_seconds if feature else None
                baseline_val = baseline.mean if baseline else None

                summary = f"Ingestion freshness delay detected on table '{incident.table_name}'."
                if actual_val is not None and baseline_val is not None:
                    actual_hours = actual_val / 3600.0
                    baseline_hours = baseline_val / 3600.0
                    root_cause = f"Actual latency was {actual_hours:.2f} hour(s) ({int(actual_val)}s), exceeding the baseline latency of {baseline_hours:.2f} hour(s)."
                else:
                    root_cause = "Pipeline run update was delayed and did not meet expected freshness SLAs."
            except Exception as e:
                logger.warning(f"Error querying freshness features: {e}")
                summary = f"Ingestion freshness delay detected on table '{incident.table_name}'."
                root_cause = "The data updates delayed past expected timelines."
                confidence = 0.8

        elif primary_driver == "anomaly":
            try:
                from backend.modules.anomaly.models import AnomalyDetection
                anomalies = db.query(AnomalyDetection).filter(
                    AnomalyDetection.pipeline_run_id == incident.pipeline_run_id
                ).all()
                anomalous_cols = [a.anomaly_type for a in anomalies if a.anomaly_type]
                cols_str = ", ".join(anomalous_cols) if anomalous_cols else "monitored columns"

                summary = f"Statistical profile anomaly flagged on table '{incident.table_name}'."
                root_cause = f"Isolation Forest model detected statistical anomaly profile deviations in: {cols_str}."
            except Exception as e:
                logger.warning(f"Error querying statistical anomalies: {e}")
                summary = f"Statistical profile anomaly flagged on table '{incident.table_name}'."
                root_cause = "Isolation Forest model flagged anomalous column profile distributions."
                confidence = 0.8

        elif primary_driver == "dbt":
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.bind)
                if not inspector.has_table("dbt_test_results", schema="test_results"):
                    logger.info("Table test_results.dbt_test_results does not exist; skipping dbt query in RCA.")
                    failed_tests = []
                    failed_count = 0
                else:
                    # Query dbt test results around incident creation time
                    start_time = incident.created_at - timedelta(minutes=5)
                    end_time = incident.created_at + timedelta(minutes=15)
                    query = text("""
                        SELECT test_name FROM test_results.dbt_test_results
                        WHERE status = 'fail'
                          AND execution_completed_at >= :start_time
                          AND execution_completed_at <= :end_time
                    """)
                    failed_tests = db.execute(query, {
                        "start_time": start_time.replace(tzinfo=None),
                        "end_time": end_time.replace(tzinfo=None)
                    }).scalars().all()
                    failed_count = len(failed_tests)

                summary = f"Downstream dbt test failures detected on table '{incident.table_name}'."
                if failed_count > 0:
                    tests_str = ", ".join(failed_tests[:5])
                    if len(failed_tests) > 5:
                        tests_str += f" and {len(failed_tests) - 5} more"
                    root_cause = f"Total of {failed_count} downstream dbt test(s) failed: {tests_str}."
                else:
                    root_cause = "Downstream dbt test failures were detected during the validation window."
            except Exception as e:
                logger.warning(f"Error querying dbt test results: {e}")
                db.rollback()
                summary = f"Downstream dbt test failures detected on table '{incident.table_name}'."
                root_cause = "Downstream dbt model verification tests failed."
                confidence = 0.8

        # Call helper methods for contributing factors and recommendations
        contributing_factors = RCAService.generate_contributing_factors(trust_score, primary_driver)
        recommendation = RCAService.generate_recommendation(primary_driver, incident.table_name)

        # Retrieve downstream impact and append to root cause
        downstream = RCAService.get_downstream_impact(db, incident.table_name)
        if downstream:
            root_cause += f" Downstream impact: {', '.join(downstream)}."

        # Determine versioning (incremental per incident)
        latest_rca = db.query(IncidentRCA).filter(
            IncidentRCA.incident_id == incident_id
        ).order_by(desc(IncidentRCA.version)).first()
        next_version = (latest_rca.version + 1) if latest_rca else 1

        db_rca = IncidentRCA(
            id=uuid.uuid4(),
            incident_id=incident_id,
            version=next_version,
            summary=summary,
            root_cause=root_cause,
            contributing_factors=contributing_factors,
            recommendation=recommendation,
            primary_penalty=primary_driver,
            confidence=confidence,
            generated_at=datetime.now(timezone.utc)
        )
        db.add(db_rca)

        # Timeline event registration
        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident_id,
            event_type="RCA_GENERATED",
            event_data={"version": next_version, "primary_penalty": primary_driver},
            created_by="system",
            created_at=datetime.now(timezone.utc)
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(db_rca)
            logger.info(
                f"Generated RCA version {next_version} for incident {incident_id}",
                extra={"incident_id": str(incident_id), "version": next_version}
            )
            return db_rca
        except Exception as exc:
            db.rollback()
            logger.error(
                f"Failed to save RCA version {next_version} for incident {incident_id}",
                exc_info=True,
                extra={"incident_id": str(incident_id)}
            )
            raise

    @staticmethod
    def _create_fallback_rca(db: Session, incident: Incident) -> IncidentRCA:
        """Helper to create a generic fallback RCA when no TrustScore is found or all penalties are 0."""
        latest_rca = db.query(IncidentRCA).filter(
            IncidentRCA.incident_id == incident.id
        ).order_by(desc(IncidentRCA.version)).first()
        next_version = (latest_rca.version + 1) if latest_rca else 1

        db_rca = IncidentRCA(
            id=uuid.uuid4(),
            incident_id=incident.id,
            version=next_version,
            summary=f"Incident opened for table '{incident.table_name}'.",
            root_cause="The incident was opened due to an automatic trigger or manual escalation.",
            contributing_factors=[],
            recommendation="Review the pipeline run logs, active data profiling results, and metrics dashboards.",
            primary_penalty="unknown",
            confidence=0.5,
            generated_at=datetime.now(timezone.utc)
        )
        db.add(db_rca)

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="RCA_GENERATED",
            event_data={"version": next_version, "primary_penalty": "unknown"},
            created_by="system",
            created_at=datetime.now(timezone.utc)
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(db_rca)
            return db_rca
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_latest(db: Session, incident_id: uuid.UUID) -> Optional[IncidentRCA]:
        """Retrieves the latest RCA analysis version for a given incident."""
        return db.query(IncidentRCA).filter(
            IncidentRCA.incident_id == incident_id
        ).order_by(desc(IncidentRCA.version)).first()

    @staticmethod
    def get_by_version(db: Session, incident_id: uuid.UUID, version: int) -> Optional[IncidentRCA]:
        """Retrieves a specific version of RCA analysis for an incident."""
        return db.query(IncidentRCA).filter(
            IncidentRCA.incident_id == incident_id,
            IncidentRCA.version == version
        ).first()

    @staticmethod
    def regenerate(db: Session, incident_id: uuid.UUID) -> IncidentRCA:
        """Forces recalculation and creates a new incremental version of RCA details."""
        return RCAService.generate_rca(db, incident_id)
