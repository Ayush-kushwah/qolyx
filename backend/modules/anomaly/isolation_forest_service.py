import uuid
import logging
import pickle
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.modules.anomaly.models import AnomalyBaseline, SilverAnomalyFeature

logger = logging.getLogger("qolyx.anomaly")


def get_feature_names(table_name: str) -> List[str]:
    """Returns the ordered, deterministic list of feature names used for a table."""
    if table_name == "bronze_financial_candles":
        return [
            "row_count",
            "freshness_latency_seconds",
            "null_rate_symbol",
            "null_rate_close_price",
            "null_rate_volume",
            "null_rate_candle_timestamp",
            "mean_close_price",
            "total_volume"
        ]
    elif table_name == "bronze_fda_events":
        return [
            "row_count",
            "freshness_latency_seconds",
            "null_rate_drug_name",
            "null_rate_reaction_description",
            "null_rate_serious",
            "null_rate_receipt_date"
        ]
    elif table_name == "bronze_github_events":
        return [
            "row_count",
            "freshness_latency_seconds",
            "null_rate_event_id",
            "null_rate_event_type",
            "null_rate_repo_name",
            "null_rate_created_at",
            "unique_events_count"
        ]
    else:
        raise ValueError(f"Unknown table name: {table_name}")


def get_model_path(table_name: str) -> str:
    """Returns the path where the Isolation Forest model pickle file will be saved.
    
    Supports Docker environment path (/app/models/) and falls back to a workspace relative
    models folder on local environments/Windows.
    """
    if os.name == "nt":
        # Windows Host: use workspace relative models directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"))
    else:
        # Unix/Docker: use /app/models
        base_dir = "/app/models"
        
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception:
        # Fallback to local workspace relative folder if permission error
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"))
        os.makedirs(base_dir, exist_ok=True)
        
    return os.path.join(base_dir, f"isolation_forest_{table_name}.pkl")


class IsolationForestService:
    """Service to train and run Isolation Forest anomaly detection models."""

    @classmethod
    def _get_exponential_decay_weights(cls, n_samples: int, decay_factor: Optional[float] = None) -> List[float]:
        if decay_factor is None:
            decay_factor = getattr(settings, 'ANOMALY_DECAY_FACTOR', 0.95)
        return [decay_factor ** i for i in range(n_samples)]

    @classmethod
    def _prepare_feature_matrix(cls, runs: List[SilverAnomalyFeature]) -> np.ndarray:
        """Converts a list of SilverAnomalyFeature objects to a numpy array for training."""
        if not runs:
            return np.empty((0, 0))
            
        table_name = runs[0].source_name
        feature_names = get_feature_names(table_name)
        matrix = []
        
        for run in runs:
            row = []
            for feature in feature_names:
                val = None
                if feature == "row_count":
                    val = run.row_count
                elif feature == "freshness_latency_seconds":
                    val = run.freshness_latency_seconds
                elif feature.startswith("null_rate_"):
                    col = feature[len("null_rate_"):]
                    val = (run.null_rates or {}).get(col)
                elif feature == "mean_close_price":
                    val = run.mean_close_price
                elif feature == "total_volume":
                    val = run.total_volume
                elif feature == "unique_events_count":
                    val = run.unique_events_count
                
                row.append(float(val) if val is not None else 0.0)
            matrix.append(row)
            
        return np.array(matrix, dtype=float)

    @classmethod
    def train_model(
        cls, 
        db: Session, 
        table_name: str, 
        force_retrain: bool = False
    ) -> Optional[AnomalyBaseline]:
        """Queries silver_anomaly_features for the last 60 runs and trains an Isolation Forest model."""
        logger.info(
            f"Starting Isolation Forest training for {table_name}",
            extra={"table_name": table_name, "force_retrain": force_retrain}
        )
        
        # Check run count in silver_anomaly_features
        runs = db.query(SilverAnomalyFeature).filter(
            SilverAnomalyFeature.source_name == table_name
        ).order_by(SilverAnomalyFeature.run_timestamp.desc()).limit(60).all()
        
        if len(runs) < 7:
            logger.warning(
                f"Insufficient runs for training {table_name}",
                extra={"table_name": table_name, "runs_count": len(runs)}
            )
            return None
            
        # 1. Prepare feature matrix
        X = cls._prepare_feature_matrix(runs)
        feature_names = get_feature_names(table_name)
        
        # 2. Train Isolation Forest model
        # Parameters specified by requirement: contamination='auto', n_estimators=100, max_samples='auto'
        weights = cls._get_exponential_decay_weights(len(runs))
        model = IsolationForest(
            contamination="auto",
            n_estimators=100,
            max_samples="auto",
            random_state=42
        )
        model.fit(X, sample_weight=weights)
        
        # 3. Save model to disk path
        model_path = get_model_path(table_name)
        try:
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
        except Exception as exc:
            logger.error(
                f"Failed to write model pickle to disk at {model_path}: {str(exc)}", 
                exc_info=True, 
                extra={"table_name": table_name}
            )
            raise
        
        # 4. Store parameters and model_path in DB
        isolation_forest_params = {
            "contamination": "auto",
            "n_estimators": 100,
            "max_samples": "auto",
            "feature_names": feature_names,
            "model_path": model_path
        }
        
        baseline = db.query(AnomalyBaseline).filter(
            AnomalyBaseline.table_name == table_name,
            AnomalyBaseline.metric_name == "isolation_forest"
        ).first()
        
        now = datetime.now(timezone.utc)
        decay_factor = getattr(settings, 'ANOMALY_DECAY_FACTOR', 0.95)
        if not baseline:
            baseline = AnomalyBaseline(
                id=uuid.uuid4(),
                table_name=table_name,
                metric_name="isolation_forest",
                feature_columns=feature_names,
                mean=0.0,
                std_dev=0.0,
                model_name="isolation_forest",
                feature_importance={},
                isolation_forest_params=isolation_forest_params,
                training_run_count=len(runs),
                last_trained_at=now,
                decay_factor=decay_factor,
                created_at=now,
                updated_at=now
            )
            db.add(baseline)
        else:
            baseline.feature_columns = feature_names
            baseline.isolation_forest_params = isolation_forest_params
            baseline.training_run_count = len(runs)
            baseline.last_trained_at = now
            baseline.model_name = "isolation_forest"
            baseline.decay_factor = decay_factor
            baseline.updated_at = now
            
        try:
            db.commit()
            db.refresh(baseline)
            logger.info(
                f"Successfully trained and saved Isolation Forest model for {table_name}",
                extra={"table_name": table_name, "runs_count": len(runs), "model_path": model_path}
            )
            return baseline
        except Exception as exc:
            db.rollback()
            logger.error(
                f"Failed to save baseline for {table_name}",
                exc_info=True,
                extra={"table_name": table_name}
            )
            raise

    @classmethod
    def is_ready(cls, db: Session, table_name: str) -> bool:
        """Returns True if model exists and training_run_count >= 7."""
        baseline = db.query(AnomalyBaseline).filter(
            AnomalyBaseline.table_name == table_name,
            AnomalyBaseline.metric_name == "isolation_forest"
        ).first()
        
        if not baseline or not baseline.isolation_forest_params:
            return False
            
        model_path = baseline.isolation_forest_params.get("model_path")
        if not model_path:
            return False
            
        return (
            baseline.training_run_count >= 7 and
            os.path.exists(model_path)
        )

    @classmethod
    def get_model_params(cls, db: Session, table_name: str) -> Optional[Dict[str, Any]]:
        """Returns the isolation_forest_params dictionary from the baseline."""
        baseline = db.query(AnomalyBaseline).filter(
            AnomalyBaseline.table_name == table_name,
            AnomalyBaseline.metric_name == "isolation_forest"
        ).first()
        
        if not baseline:
            return None
            
        return baseline.isolation_forest_params

    @classmethod
    def get_anomaly_score(cls, db: Session, table_name: str, feature_values: Dict[str, Any]) -> float:
        """Uses the trained model's decision_function() to compute the anomaly score.
        
        Normalizes the score to a 0-1 range (higher = more anomalous).
        """
        params = cls.get_model_params(db, table_name)
        if not params or "model_path" not in params:
            logger.warning(f"No trained Isolation Forest model found for {table_name}")
            return 0.0
            
        model_path = params["model_path"]
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at path: {model_path}")
            return 0.0
            
        # Deserialize model
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
        except Exception as exc:
            logger.error(f"Failed to deserialize model for {table_name}: {str(exc)}", exc_info=True)
            return 0.0
            
        # Prepare feature vector matching the model's feature names
        feature_names = params.get("feature_names") or get_feature_names(table_name)
        vector = []
        for feature in feature_names:
            val = None
            if feature == "row_count":
                val = feature_values.get("row_count")
            elif feature == "freshness_latency_seconds":
                val = feature_values.get("freshness_latency_seconds")
            elif feature.startswith("null_rate_"):
                col = feature[len("null_rate_"):]
                val = (feature_values.get("null_rates") or {}).get(col)
            elif feature == "mean_close_price":
                val = feature_values.get("mean_close_price")
            elif feature == "total_volume":
                val = feature_values.get("total_volume")
            elif feature == "unique_events_count":
                val = feature_values.get("unique_events_count")
                
            vector.append(float(val) if val is not None else 0.0)
            
        # Compute decision function score
        X = np.array([vector], dtype=float)
        decision_score = float(model.decision_function(X)[0])
        
        # Normalize to [0.0, 1.0] where higher is more anomalous.
        normalized_score = min(max(0.5 - decision_score, 0.0), 1.0)
        
        return normalized_score
