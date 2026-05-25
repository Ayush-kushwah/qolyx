import pytest
import uuid
import os
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
import numpy as np
from sklearn.ensemble import IsolationForest

from backend.core.database import Base
from backend.modules.anomaly.models import AnomalyBaseline, AnomalyDetection, SilverAnomalyFeature
from backend.modules.anomaly.isolation_forest_service import IsolationForestService, get_feature_names
from backend.modules.anomaly.baseline_service import AnomalyBaselineService
from backend.modules.anomaly.detection_service import detect_anomalies
from backend.modules.anomaly.feature_service import get_feature_vector
from backend.modules.anomaly.shap_service import SHAPService


@pytest.fixture(scope="function")
def db_session():
    """Fixture to create an in-memory SQLite database, run migrations, and yield a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def patch_model_path(tmp_path):
    """Autouse fixture to redirect model pkl files to a pytest temp directory to keep workspace clean."""
    temp_dir = tmp_path / "models"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    def mock_get_model_path(table_name: str) -> str:
        return os.path.join(str(temp_dir), f"isolation_forest_{table_name}.pkl")
        
    with patch("backend.modules.anomaly.isolation_forest_service.get_model_path", side_effect=mock_get_model_path):
        yield


@pytest.fixture(autouse=True)
def mock_publish():
    """Fixture to auto-mock the publish function to avoid Redis/event-bus dependencies during tests."""
    with patch("backend.modules.anomaly.detection_service.publish") as mock:
        yield mock


def insert_mock_runs(db, table_name, count=10):
    """Helper to insert mock historical SilverAnomalyFeature runs for baseline training."""
    now = datetime.now(timezone.utc)
    for i in range(count):
        run_time = now - timedelta(minutes=5 * (count - i))
        null_rates = {
            "symbol": 0.0,
            "close_price": 0.0,
            "volume": 0.0,
            "candle_timestamp": 0.0,
            "drug_name": 0.0,
            "reaction_description": 0.0,
            "serious": 0.0,
            "receipt_date": 0.0,
            "event_id": 0.0,
            "event_type": 0.0,
            "repo_name": 0.0,
            "created_at": 0.0,
        }
        run = SilverAnomalyFeature(
            pipeline_run_id=uuid.uuid4(),
            source_name=table_name,
            row_count=100 + i,
            null_rates=null_rates,
            mean_close_price=150.0 + i * 0.1,
            total_volume=1000 + i * 10,
            unique_events_count=100 + i,
            freshness_latency_seconds=30.0,
            run_timestamp=run_time
        )
        db.add(run)
    db.commit()


def test_train_model_insufficient_runs(db_session):
    """Test train_model fails and returns None when historical run count < 7."""
    table_name = "bronze_financial_candles"
    insert_mock_runs(db_session, table_name, count=5)
    
    baseline = IsolationForestService.train_model(db_session, table_name)
    assert baseline is None
    
    # Via baseline service
    res = AnomalyBaselineService.train_baseline(db_session, table_name)
    assert res.training_completed is False


def test_train_model_success(db_session):
    """Test train_model successfully trains a model and stores baseline with correct features."""
    table_name = "bronze_financial_candles"
    insert_mock_runs(db_session, table_name, count=12)
    
    baseline = IsolationForestService.train_model(db_session, table_name)
    assert baseline is not None
    assert baseline.table_name == table_name
    assert baseline.model_name == "isolation_forest"
    assert baseline.training_run_count == 12
    assert baseline.feature_columns == get_feature_names(table_name)
    
    # Verify baseline record has valid isolation_forest_params
    params = baseline.isolation_forest_params
    assert params["contamination"] == "auto"
    assert params["n_estimators"] == 100
    assert params["max_samples"] == "auto"
    assert "model_path" in params
    assert os.path.exists(params["model_path"])


def test_is_ready(db_session):
    """Test is_ready returns False before training and True after training."""
    table_name = "bronze_fda_events"
    
    # Initially False
    assert IsolationForestService.is_ready(db_session, table_name) is False
    
    # Insert runs and train
    insert_mock_runs(db_session, table_name, count=8)
    baseline = IsolationForestService.train_model(db_session, table_name)
    assert baseline is not None
    
    # Now True
    assert IsolationForestService.is_ready(db_session, table_name) is True


def test_get_anomaly_score(db_session):
    """Test get_anomaly_score returns a float value between 0.0 and 1.0."""
    table_name = "bronze_financial_candles"
    insert_mock_runs(db_session, table_name, count=15)
    baseline = IsolationForestService.train_model(db_session, table_name)
    assert baseline is not None
    
    normal_features = {
        "row_count": 105,
        "freshness_latency_seconds": 30.0,
        "null_rates": {
            "symbol": 0.0,
            "close_price": 0.0,
            "volume": 0.0,
            "candle_timestamp": 0.0
        },
        "mean_close_price": 150.5,
        "total_volume": 1050
    }
    
    score = IsolationForestService.get_anomaly_score(db_session, table_name, normal_features)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_detect_anomalies_workflow(db_session, mock_publish):
    """Test detect_anomalies workflow for normal runs, not ready cases, and actual anomalies."""
    table_name = "bronze_github_events"
    run_id = uuid.uuid4()
    
    normal_features = {
        "row_count": 105,
        "freshness_latency_seconds": 30.0,
        "null_rates": {
            "event_id": 0.0,
            "event_type": 0.0,
            "repo_name": 0.0,
            "created_at": 0.0
        },
        "unique_events_count": 105
    }
    
    # Case 1: Model not ready -> returns None
    detection = detect_anomalies(db_session, run_id, table_name, normal_features)
    assert detection is None
    
    # Train the baseline
    insert_mock_runs(db_session, table_name, count=15)
    IsolationForestService.train_model(db_session, table_name)
    
    # Case 2: Normal run -> returns None (no anomaly)
    detection_normal = detect_anomalies(db_session, run_id, table_name, normal_features)
    assert detection_normal is None
    
    # Case 3: Anomalous run -> returns AnomalyDetection and publishes detection event
    anomalous_features = {
        "row_count": 10000,
        "freshness_latency_seconds": 9999.0,
        "null_rates": {
            "event_id": 99.0,
            "event_type": 99.0,
            "repo_name": 99.0,
            "created_at": 99.0
        },
        "unique_events_count": 10
    }
    
    detection_anom = detect_anomalies(db_session, run_id, table_name, anomalous_features)
    assert detection_anom is not None
    assert detection_anom.pipeline_run_id == run_id
    assert detection_anom.table_name == table_name
    assert detection_anom.anomaly_score > 0.0
    assert detection_anom.explanation is not None
    
    # Verify event published
    assert mock_publish.called
    published_event_type, published_payload = mock_publish.call_args[0]
    assert published_event_type == "anomaly.detected"
    assert published_payload["pipeline_run_id"] == str(run_id)
    assert published_payload["table_name"] == table_name


def test_get_feature_vector_all_tables():
    """Test get_feature_vector returns correct ordered list for all three tables."""
    # 1. Candles
    candles_features = {
        "row_count": 100,
        "freshness_latency_seconds": 30.0,
        "null_rates": {
            "symbol": 0.1,
            "close_price": 0.2,
            "volume": 0.3,
            "candle_timestamp": 0.4
        },
        "mean_close_price": 150.0,
        "total_volume": 1000
    }
    v1 = get_feature_vector(candles_features, "bronze_financial_candles")
    assert v1 == [100.0, 30.0, 0.1, 0.2, 0.3, 0.4, 150.0, 1000.0]
    
    # 2. FDA Events
    fda_features = {
        "row_count": 50,
        "freshness_latency_seconds": 45.0,
        "null_rates": {
            "drug_name": 0.5,
            "reaction_description": 0.6,
            "serious": 0.7,
            "receipt_date": 0.8
        }
    }
    v2 = get_feature_vector(fda_features, "bronze_fda_events")
    assert v2 == [50.0, 45.0, 0.5, 0.6, 0.7, 0.8]
    
    # 3. GitHub Events
    github_features = {
        "row_count": 200,
        "freshness_latency_seconds": 15.0,
        "null_rates": {
            "event_id": 0.11,
            "event_type": 0.12,
            "repo_name": 0.13,
            "created_at": 0.14
        },
        "unique_events_count": 195
    }
    v3 = get_feature_vector(github_features, "bronze_github_events")
    assert v3 == [200.0, 15.0, 0.11, 0.12, 0.13, 0.14, 195.0]


def test_shap_explainability_service():
    """Test SHAPService.explain_anomaly returns feature importance and generate_explanation produces a string."""
    # Fit a simple Isolation Forest
    X = np.random.normal(size=(20, 3))
    model = IsolationForest(n_estimators=10, random_state=42)
    model.fit(X)
    
    feature_names = ["row_count", "freshness_latency_seconds", "mean_close_price"]
    feature_values = {
        "row_count": 1.0,
        "freshness_latency_seconds": 2.0,
        "mean_close_price": 3.0
    }
    
    importance = SHAPService.explain_anomaly(model, feature_values, feature_names)
    assert len(importance) == 3
    assert all(isinstance(v, float) for v in importance.values())
    
    # Verify generate_explanation
    explanation = SHAPService.generate_explanation(importance, 0.85, "volume_spike")
    assert isinstance(explanation, str)
    assert "Anomaly of type 'volume_spike' detected with score 0.85." in explanation


def test_exponential_decay_weights():
    from backend.modules.anomaly.isolation_forest_service import IsolationForestService
    
    weights = IsolationForestService._get_exponential_decay_weights(5, 0.95)
    expected = [1.0, 0.95, 0.9025, 0.857375, 0.81450625]
    for w, e in zip(weights, expected):
        assert abs(w - e) < 0.0001
    
    weights = IsolationForestService._get_exponential_decay_weights(1, 0.95)
    assert weights == [1.0]
    
    weights = IsolationForestService._get_exponential_decay_weights(3, 0.9)
    assert weights == [1.0, 0.9, 0.81]
    
    weights = IsolationForestService._get_exponential_decay_weights(3)
    assert weights == [1.0, 0.95, 0.9025]
