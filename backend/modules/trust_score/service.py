import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.events import publish_with_retry
from backend.modules.trust_score.models import TrustScore
from backend.modules.trust_score.schemas import TrustScoreCreate, TrustScoreResponse
from backend.modules.contracts.models import ContractViolation
from backend.modules.anomaly.models import AnomalyDetection

logger = logging.getLogger("qolyx.trust_score")

# Constants
CAP_CONTRACT = 40
CAP_ANOMALY = 20
CAP_FRESHNESS = 30
CAP_VOLUME = 30
CAP_DBT = 20
CAP_TOTAL = 100

TRUST_SCORE_HEALTHY = 80
TRUST_SCORE_WARNING = 60
TRUST_SCORE_DEGRADED = 40
TRUST_SCORE_CRITICAL = 0

EVENT_RETRY_COUNT = 3
EVENT_RETRY_DELAY_SECONDS = 0.5
SLOW_CALCULATION_THRESHOLD_SECONDS = 1.0
SCORE_CHANGE_AUDIT_THRESHOLD = 10

TRUST_SCORE_CALCULATION_MAX_RETRIES = 3


class TrustScoreService:
    """Service to calculate, cap, save, and retrieve Qolyx Trust Scores and penalty breakdowns."""

    @staticmethod
    def _validate_and_cap_penalties(penalties: Dict[str, int]) -> Dict[str, int]:
        """Validates that each individual penalty type does not exceed its maximum cap.
        
        Logs a warning and caps the value if it exceeds the maximum.
        """
        caps = {
            "contract_penalty": CAP_CONTRACT,
            "anomaly_penalty": CAP_ANOMALY,
            "freshness_penalty": CAP_FRESHNESS,
            "volume_penalty": CAP_VOLUME,
            "dbt_penalty": CAP_DBT
        }
        capped_penalties = {}
        for key, val in penalties.items():
            cap = caps.get(key, 100)
            if val > cap:
                logger.warning(
                    f"Penalty '{key}' value {val} exceeds cap of {cap}. Capping to max.",
                    extra={"penalty_key": key, "original_value": val, "cap": cap}
                )
                capped_penalties[key] = cap
            else:
                capped_penalties[key] = val
        return capped_penalties

    @staticmethod
    def _get_status_from_score(score: int) -> str:
        """Classifies the trust score status mapping (HEALTHY, WARNING, DEGRADED, CRITICAL)."""
        if score >= TRUST_SCORE_HEALTHY:
            return "HEALTHY"
        elif score >= TRUST_SCORE_WARNING:
            return "WARNING"
        elif score >= TRUST_SCORE_DEGRADED:
            return "DEGRADED"
        else:
            return "CRITICAL"

    @staticmethod
    def _validate_penalties_structure(penalties: Dict[str, int]) -> None:
        """Validates that the penalties dictionary structure has all required keys and positive values."""
        if not isinstance(penalties, dict):
            raise ValueError("Penalties must be a dictionary.")
        
        required_keys = {
            "contract_penalty",
            "anomaly_penalty",
            "dbt_penalty",
            "freshness_penalty",
            "volume_penalty"
        }
        missing_keys = required_keys - set(penalties.keys())
        if missing_keys:
            raise ValueError(f"Missing required penalty keys: {missing_keys}")
            
        for key in required_keys:
            val = penalties[key]
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"Penalty '{key}' must be a non-negative integer. Got: {val}")

    @staticmethod
    def _get_baseline_for_metric(db: Session, table_name: str, metric_name: str) -> Optional[Dict[str, float]]:
        """Queries the anomaly_baselines table for mean and std_dev of a given metric."""
        try:
            from backend.modules.anomaly.models import AnomalyBaseline
            baseline = db.query(AnomalyBaseline).filter(
                AnomalyBaseline.table_name == table_name,
                AnomalyBaseline.metric_name == metric_name
            ).first()
            if baseline:
                return {
                    "mean": float(baseline.mean),
                    "std_dev": float(baseline.std_dev)
                }
            return None
        except Exception as exc:
            logger.warning(
                f"Failed to query baseline for metric '{metric_name}' in table '{table_name}'; returning None: {str(exc)}",
                exc_info=True,
                extra={"table_name": table_name, "metric_name": metric_name}
            )
            return None

    @staticmethod
    def _calculate_penalty_from_zscore(zscore: float, max_penalty: int) -> int:
        """Calculates integer penalty capped at max_penalty using Z-score deviation."""
        zscore = abs(zscore)
        penalty = min(int(zscore * (max_penalty / 3.0)), max_penalty)
        return max(0, penalty)

    @staticmethod
    def calculate_penalties(
        db: Session,
        pipeline_run_id: uuid.UUID,
        table_name: str,
        run_created_at: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Queries contract violations and anomaly detections to calculate raw metrics."""
        logger.info(
            "Calculating penalties",
            extra={"pipeline_run_id": str(pipeline_run_id), "table_name": table_name}
        )
        
        # 1. Contract Penalty from contract_violations
        contract_penalty = 0
        try:
            sum_violations = db.query(func.sum(ContractViolation.penalty_amount)).filter(
                ContractViolation.pipeline_run_id == pipeline_run_id
            ).scalar()
            contract_penalty = int(sum_violations) if sum_violations is not None else 0
            if contract_penalty > CAP_CONTRACT:
                contract_penalty = CAP_CONTRACT
        except Exception as exc:
            logger.error(
                "Failed to calculate contract violations penalty; defaulting to 0",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )
            contract_penalty = 0
            
        # 2. Anomaly Penalty from anomaly_detections
        anomaly_penalty = 0
        try:
            sum_anomalies = db.query(func.sum(AnomalyDetection.anomaly_penalty)).filter(
                AnomalyDetection.pipeline_run_id == pipeline_run_id,
                AnomalyDetection.is_false_positive == False
            ).scalar()
            anomaly_penalty = int(sum_anomalies) if sum_anomalies is not None else 0
            if anomaly_penalty > CAP_ANOMALY:
                anomaly_penalty = CAP_ANOMALY
        except Exception as exc:
            logger.error(
                "Failed to calculate anomaly detections penalty; defaulting to 0",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )
            anomaly_penalty = 0
            
        # 3. DBT Penalty
        dbt_penalty = 0
        try:
            from sqlalchemy import text
            from datetime import timedelta
            
            if run_created_at is None:
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(minutes=15)
            else:
                if run_created_at.tzinfo is None:
                    run_created_at = run_created_at.replace(tzinfo=timezone.utc)
                start_time = run_created_at
                end_time = run_created_at + timedelta(minutes=15)
                
            # Convert to naive UTC datetimes for database compatibility
            start_naive = start_time.astimezone(timezone.utc).replace(tzinfo=None)
            end_naive = end_time.astimezone(timezone.utc).replace(tzinfo=None)
            
            query = text("""
                SELECT COUNT(*) FROM test_results.dbt_test_results
                WHERE status = 'fail'
                  AND execution_completed_at >= :start_time
                  AND execution_completed_at <= :end_time
            """)
            failed_count = db.scalar(query, {"start_time": start_naive, "end_time": end_naive})
            failed_count = int(failed_count) if failed_count is not None else 0
            
            dbt_penalty = min(failed_count * 7, CAP_DBT)
            
            logger.info(
                "Calculated DBT test failure penalty",
                extra={
                    "pipeline_run_id": str(pipeline_run_id),
                    "failed_count": failed_count,
                    "dbt_penalty": dbt_penalty,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to calculate DBT test failures penalty; defaulting to 0",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )
            dbt_penalty = 0
        
        # 4. Freshness Penalty
        freshness_penalty = 0
        try:
            from backend.modules.anomaly.models import SilverAnomalyFeature
            feature = db.query(SilverAnomalyFeature).filter(
                SilverAnomalyFeature.pipeline_run_id == pipeline_run_id
            ).first()
            
            if feature and feature.freshness_latency_seconds is not None:
                val = float(feature.freshness_latency_seconds)
                baseline = TrustScoreService._get_baseline_for_metric(db, table_name, "freshness_latency_seconds")
                if baseline:
                    mean = baseline["mean"]
                    std_dev = baseline["std_dev"]
                    zscore = abs(val - mean) / (std_dev + 1e-8)
                    freshness_penalty = TrustScoreService._calculate_penalty_from_zscore(zscore, CAP_FRESHNESS)
                    logger.info(
                        "Calculated freshness penalty from baseline",
                        extra={
                            "pipeline_run_id": str(pipeline_run_id),
                            "freshness_latency_seconds": val,
                            "mean": mean,
                            "std_dev": std_dev,
                            "zscore": zscore,
                            "freshness_penalty": freshness_penalty
                        }
                    )
                else:
                    logger.warning(
                        "Baseline missing for metric 'freshness_latency_seconds'; defaulting to 0 freshness penalty",
                        extra={"pipeline_run_id": str(pipeline_run_id), "table_name": table_name}
                    )
            else:
                logger.warning(
                    "No feature record or freshness latency found for run; defaulting to 0 freshness penalty",
                    extra={"pipeline_run_id": str(pipeline_run_id)}
                )
        except Exception as exc:
            logger.warning(
                f"Failed to calculate freshness penalty; defaulting to 0: {str(exc)}",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )
            freshness_penalty = 0
        
        # 5. Volume Penalty
        volume_penalty = 0
        try:
            from backend.modules.anomaly.models import SilverAnomalyFeature
            feature = db.query(SilverAnomalyFeature).filter(
                SilverAnomalyFeature.pipeline_run_id == pipeline_run_id
            ).first()
            
            if feature and feature.row_count is not None:
                val = float(feature.row_count)
                baseline = TrustScoreService._get_baseline_for_metric(db, table_name, "row_count")
                if baseline:
                    mean = baseline["mean"]
                    std_dev = baseline["std_dev"]
                    zscore = abs(val - mean) / (std_dev + 1e-8)
                    volume_penalty = TrustScoreService._calculate_penalty_from_zscore(zscore, CAP_VOLUME)
                    logger.info(
                        "Calculated volume penalty from baseline",
                        extra={
                            "pipeline_run_id": str(pipeline_run_id),
                            "row_count": val,
                            "mean": mean,
                            "std_dev": std_dev,
                            "zscore": zscore,
                            "volume_penalty": volume_penalty
                        }
                    )
                else:
                    logger.warning(
                        "Baseline missing for metric 'row_count'; defaulting to 0 volume penalty",
                        extra={"pipeline_run_id": str(pipeline_run_id), "table_name": table_name}
                    )
            else:
                logger.warning(
                    "No feature record or row count found for run; defaulting to 0 volume penalty",
                    extra={"pipeline_run_id": str(pipeline_run_id)}
                )
        except Exception as exc:
            logger.warning(
                f"Failed to calculate volume penalty; defaulting to 0: {str(exc)}",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )
            volume_penalty = 0
        
        return {
            "contract_penalty": contract_penalty,
            "anomaly_penalty": anomaly_penalty,
            "dbt_penalty": dbt_penalty,
            "freshness_penalty": freshness_penalty,
            "volume_penalty": volume_penalty
        }

    @staticmethod
    def calculate_trust_score(penalties: Dict[str, int]) -> Tuple[int, int, str]:
        """Validates, caps, sums penalties and returns (trust_score, total_penalty, status)."""
        TrustScoreService._validate_penalties_structure(penalties)
        capped_penalties = TrustScoreService._validate_and_cap_penalties(penalties)
        total_penalty = sum(capped_penalties.values())
        total_penalty = min(total_penalty, CAP_TOTAL)
        trust_score = 100 - total_penalty
        status = TrustScoreService._get_status_from_score(trust_score)
        return trust_score, total_penalty, status

    @staticmethod
    def save_trust_score(
        db: Session,
        pipeline_run_id: uuid.UUID,
        table_name: str,
        penalties: Dict[str, int],
        trust_score: int,
        total_penalty: int,
        status: str
    ) -> TrustScore:
        """Idempotently saves or updates the trust score record and publishes event on commit."""
        logger.info(
            "Saving trust score",
            extra={
                "pipeline_run_id": str(pipeline_run_id),
                "table_name": table_name,
                "trust_score": trust_score,
                "status": status
            }
        )
        
        now = datetime.now(timezone.utc)
        
        # Check for existing record by pipeline_run_id (idempotency)
        existing = db.query(TrustScore).filter(
            TrustScore.pipeline_run_id == pipeline_run_id
        ).first()
        
        previous_score: Optional[int] = None
        
        if existing:
            previous_score = existing.trust_score
            existing.contract_penalty = penalties.get("contract_penalty", 0)
            existing.freshness_penalty = penalties.get("freshness_penalty", 0)
            existing.volume_penalty = penalties.get("volume_penalty", 0)
            existing.anomaly_penalty = penalties.get("anomaly_penalty", 0)
            existing.dbt_penalty = penalties.get("dbt_penalty", 0)
            existing.total_penalty = total_penalty
            existing.trust_score = trust_score
            existing.trust_score_status = status
            existing.updated_at = now
            record = existing
        else:
            record = TrustScore(
                id=uuid.uuid4(),
                pipeline_run_id=pipeline_run_id,
                table_name=table_name,
                contract_penalty=penalties.get("contract_penalty", 0),
                freshness_penalty=penalties.get("freshness_penalty", 0),
                volume_penalty=penalties.get("volume_penalty", 0),
                anomaly_penalty=penalties.get("anomaly_penalty", 0),
                dbt_penalty=penalties.get("dbt_penalty", 0),
                total_penalty=total_penalty,
                trust_score=trust_score,
                trust_score_status=status,
                created_at=now,
                updated_at=now
            )
            db.add(record)
            
        try:
            db.commit()
            db.refresh(record)
            
            # Emit trust_score.calculated event
            event_payload = {
                "pipeline_run_id": str(record.pipeline_run_id),
                "table_name": record.table_name,
                "trust_score": record.trust_score,
                "total_penalty": record.total_penalty,
                "trust_score_status": record.trust_score_status,
                "breakdown": record.breakdown
            }
            publish_with_retry("trust_score.calculated", event_payload)
            
            # Audit score change
            TrustScoreService._audit_score_change(previous_score, record.trust_score, record.pipeline_run_id)
            
            return record
        except Exception as exc:
            db.rollback()
            logger.error(
                "Failed to save trust score record",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )
            raise

    @staticmethod
    def get_trust_score_for_run(db: Session, pipeline_run_id: uuid.UUID) -> Optional[TrustScore]:
        """Queries database for TrustScore using pipeline_run_id."""
        return db.query(TrustScore).filter(TrustScore.pipeline_run_id == pipeline_run_id).first()

    @staticmethod
    def get_trust_score_history(
        db: Session,
        table_name: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Retrieves paginated history for a table ordered by created_at desc."""
        if page < 1:
            raise ValueError("Page number must be 1 or greater.")
        if page_size < 1 or page_size > 100:
            raise ValueError("Page size must be between 1 and 100.")
            
        query = db.query(TrustScore).filter(TrustScore.table_name == table_name)
        total = query.count()
        
        import math
        pages = math.ceil(total / page_size) if total > 0 else 1
        
        items = query.order_by(TrustScore.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }

    @staticmethod
    def _audit_score_change(previous_score: Optional[int], new_score: int, pipeline_run_id: uuid.UUID) -> None:
        """Audits large score movements and logs warning warnings if it shifts by >= 10 points."""
        if previous_score is not None:
            diff = abs(previous_score - new_score)
            if diff >= SCORE_CHANGE_AUDIT_THRESHOLD:
                logger.warning(
                    f"Significant trust score change detected for pipeline run: {pipeline_run_id}. "
                    f"Previous score: {previous_score}, New score: {new_score} (Difference: {diff}).",
                    extra={
                        "pipeline_run_id": str(pipeline_run_id),
                        "previous_score": previous_score,
                        "new_score": new_score,
                        "difference": diff
                    }
                )

    @staticmethod
    def _log_performance(start_time: float, pipeline_run_id: uuid.UUID) -> None:
        """Logs a performance warning if the score calculation duration exceeds the threshold."""
        duration = time.time() - start_time
        if duration > SLOW_CALCULATION_THRESHOLD_SECONDS:
            logger.warning(
                f"Slow trust score calculation performance for run {pipeline_run_id}: {duration:.4f}s exceeds threshold of {SLOW_CALCULATION_THRESHOLD_SECONDS}s.",
                extra={
                    "pipeline_run_id": str(pipeline_run_id),
                    "duration_seconds": duration,
                    "threshold_seconds": SLOW_CALCULATION_THRESHOLD_SECONDS
                }
            )
