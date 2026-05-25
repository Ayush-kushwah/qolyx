import logging
from typing import Dict
from sqlalchemy.orm import Session

from backend.modules.anomaly.models import AnomalyBaseline
from backend.modules.anomaly.schemas import BaselineTrainingResponse
from backend.modules.anomaly.isolation_forest_service import IsolationForestService

logger = logging.getLogger("qolyx.anomaly")


class AnomalyBaselineService:
    """Service to train and manage anomaly baselines using Isolation Forest."""

    @classmethod
    def is_baseline_ready(cls, db: Session, table_name: str) -> bool:
        """Checks if the Isolation Forest baseline model is trained and ready."""
        return IsolationForestService.is_ready(db, table_name)

    @classmethod
    def get_baseline(cls, db: Session, table_name: str) -> Dict[str, AnomalyBaseline]:
        """Retrieves the baseline model record for a given table."""
        baseline = db.query(AnomalyBaseline).filter(
            AnomalyBaseline.table_name == table_name,
            AnomalyBaseline.metric_name == "isolation_forest"
        ).first()
        if not baseline:
            return {}
        return {baseline.metric_name: baseline}

    @classmethod
    def train_baseline(
        cls, 
        db: Session, 
        table_name: str, 
        force_retrain: bool = False
    ) -> BaselineTrainingResponse:
        """Trains the Isolation Forest model on historical features and stores parameters."""
        try:
            baseline = IsolationForestService.train_model(
                db=db,
                table_name=table_name,
                force_retrain=force_retrain
            )
            
            if not baseline:
                return BaselineTrainingResponse(
                    table_name=table_name,
                    features_count=0,
                    training_run_count=0,
                    training_completed=False
                )
                
            return BaselineTrainingResponse(
                table_name=table_name,
                features_count=len(baseline.feature_columns),
                training_run_count=baseline.training_run_count,
                training_completed=True
            )
        except Exception as exc:
            logger.error(
                f"Failed to train baseline for {table_name}: {str(exc)}", 
                exc_info=True, 
                extra={"table_name": table_name}
            )
            return BaselineTrainingResponse(
                table_name=table_name,
                features_count=0,
                training_run_count=0,
                training_completed=False
            )
