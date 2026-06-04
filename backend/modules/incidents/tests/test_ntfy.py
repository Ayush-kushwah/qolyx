import pytest
import uuid
import base64
import httpx
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.core.database import Base
from backend.core.config import settings
from backend.modules.incidents.models import SystemSettings, AlertConfig, Incident, IncidentRCA
from backend.utils.ntfy_topic import get_or_create_ntfy_topic
from backend.modules.incidents.alert_service import AlertService
from backend.main import app


@pytest.fixture(scope="function")
def db_session():
    """Fixture to create an in-memory SQLite database, register models, and yield a session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    # Ensure models are imported so they are registered on Base.metadata
    Base.metadata.create_all(bind=engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def mock_session_local(db_session):
    """Automatically patch SessionLocal to use the test SQLite db_session."""
    with patch("backend.utils.ntfy_topic.SessionLocal", return_value=db_session):
        yield


def test_get_or_create_ntfy_topic_settings():
    """Test 1: Returns the topic if settings.NTFY_TOPIC is set."""
    with patch.object(settings, "NTFY_TOPIC", "settings_configured_topic"):
        topic = get_or_create_ntfy_topic()
        assert topic == "settings_configured_topic"


def test_get_or_create_ntfy_topic_db(db_session):
    """Test 2: Returns the topic from the database if settings topic is empty but DB record exists."""
    with patch.object(settings, "NTFY_TOPIC", ""):
        # Seed ntfy_topic in DB
        db_session.add(
            SystemSettings(
                id=uuid.uuid4(),
                key="ntfy_topic",
                value="db_stored_topic",
                updated_at=datetime.now(timezone.utc)
            )
        )
        db_session.commit()

        topic = get_or_create_ntfy_topic()
        assert topic == "db_stored_topic"


def test_get_or_create_ntfy_topic_generated(db_session):
    """Test 3: Generates and stores a new topic if both settings and DB are empty."""
    with patch.object(settings, "NTFY_TOPIC", ""):
        topic = get_or_create_ntfy_topic()
        
        # Verify format: qolyx_alerts_xxxxxxxx
        assert topic.startswith("qolyx_alerts_")
        assert len(topic) == len("qolyx_alerts_") + 8
        
        # Verify that it got persisted in the database
        record = db_session.query(SystemSettings).filter(SystemSettings.key == "ntfy_topic").first()
        assert record is not None
        assert record.value == topic


def test_get_or_create_ntfy_topic_fallback(db_session):
    """Test 4: Falls back to qolyx_alerts_default when database operations raise an exception."""
    with patch.object(settings, "NTFY_TOPIC", ""):
        # Patch SessionLocal to fail
        with patch("backend.utils.ntfy_topic.SessionLocal", side_effect=Exception("DB Failure")):
            topic = get_or_create_ntfy_topic()
            assert topic == "qolyx_alerts_default"


def test_send_ntfy_alert_success():
    """Test 5: Checks if _send_ntfy returns True when the HTTP post request succeeds (status 200)."""
    incident = Incident(
        id=uuid.uuid4(),
        pipeline_run_id=uuid.uuid4(),
        title="Critical Anomaly Detected",
        table_name="bronze_financial_candles",
        severity="CRITICAL",
        state="OPEN",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    rca = IncidentRCA(
        id=uuid.uuid4(),
        incident_id=incident.id,
        summary="Summary of anomaly",
        root_cause="Volume dropped significantly below baseline",
        recommendation="Verify ingestion task pipelines",
        version=1,
        primary_penalty="anomaly_penalty",
        generated_at=datetime.now(timezone.utc)
    )

    with patch.object(settings, "NTFY_ENABLED", True), \
         patch.object(settings, "NTFY_HOST", "http://ntfy-test-host"), \
         patch("backend.modules.incidents.alert_service.get_or_create_ntfy_topic", return_value="mock_topic"), \
         patch("httpx.post") as mock_post:
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = AlertService._send_ntfy(incident, rca)
        assert result is True
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://ntfy-test-host/mock_topic"
        assert b"Root Cause: Volume dropped significantly below baseline" in kwargs["content"]
        assert kwargs["headers"]["Priority"] == "5"


def test_send_ntfy_alert_failure():
    """Test 6: Checks if _send_ntfy gracefully returns False on request error or non-200 status."""
    incident = Incident(
        id=uuid.uuid4(),
        pipeline_run_id=uuid.uuid4(),
        title="High Latency Detected",
        table_name="bronze_fda_events",
        severity="HIGH",
        state="OPEN",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    with patch.object(settings, "NTFY_ENABLED", True), \
         patch("backend.modules.incidents.alert_service.get_or_create_ntfy_topic", return_value="mock_topic"):
        
        # Scenario A: Non-200 HTTP Response
        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Error"
            mock_post.return_value = mock_response

            result = AlertService._send_ntfy(incident)
            assert result is False

        # Scenario B: Request exception thrown
        with patch("httpx.post", side_effect=httpx.RequestError("Timeout")):
            result = AlertService._send_ntfy(incident)
            assert result is False


def test_ntfy_topic_endpoint():
    """Test 7: GET /api/incidents/ntfy/topic returns the correct topic name and public subscribe URL."""
    client = TestClient(app)
    with patch.object(settings, "NTFY_TOPIC", "api_configured_topic"):
        response = client.get("/api/incidents/ntfy/topic")
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "api_configured_topic"
        assert data["url"] == "https://ntfy.sh/api_configured_topic"


def test_ntfy_qrcode_endpoint():
    """Test 8: GET /api/incidents/ntfy/qrcode returns base64 image data and metadata."""
    client = TestClient(app)
    with patch.object(settings, "NTFY_TOPIC", "qrcode_test_topic"):
        response = client.get("/api/incidents/ntfy/qrcode")
        assert response.status_code == 200
        data = response.json()
        assert "qr_code" in data
        assert data["qr_code"].startswith("data:image/png;base64,")
        assert data["topic"] == "qrcode_test_topic"
        assert data["url"] == "https://ntfy.sh/qrcode_test_topic"

        # Verify decoding of generated base64 image
        header, encoded = data["qr_code"].split(",", 1)
        decoded_bytes = base64.b64decode(encoded)
        assert len(decoded_bytes) > 0


def test_seed_default_alert_config(db_session):
    """Test 9: seed_default_alert_config creates a default Ntfy configuration if none exists."""
    from backend.main import seed_default_alert_config
    
    with patch("backend.core.database.SessionLocal", return_value=db_session):
        # Initial run: should seed Ntfy default config
        seed_default_alert_config()
        config = db_session.query(AlertConfig).filter(AlertConfig.channel_type == "ntfy").first()
        assert config is not None
        assert config.name == "Ntfy Default"
        assert config.is_active is True
        assert config.severity_threshold == "MEDIUM"

        # Second run: should not duplicate config
        seed_default_alert_config()
        count = db_session.query(AlertConfig).filter(AlertConfig.channel_type == "ntfy").count()
        assert count == 1
