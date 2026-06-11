import pytest
import uuid
import json
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.core.database import Base, get_db
from backend.core.config import settings as app_settings

# Use a local SQLite database for testing.
DB_FILE = "test_qolyx.db"
engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def init_db():
    # Import all models to register them on Base.metadata
    from backend.modules.users.models import User, ApiKey, UserSession, LoginHistory, IntegrationConnection
    from backend.modules.incidents.models import SystemSettings, AlertConfig
    from backend.modules.contracts.models import Contract, ContractViolation
    from backend.modules.anomaly.models import AnomalyDetection, AnomalyBaseline, AnomalyFeedback
    from backend.modules.trust_score.models import TrustScore

    # Clean the schema completely before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    # Seed default user for dependencies/auth
    from backend.modules.users.utils import hash_password
    hashed = hash_password("adminpassword123")
    user = User(
        id=uuid.uuid4(),
        name="Administrator",
        email="admin@qolyx.io",
        username="admin",
        hashed_password=hashed,
        avatar_url=None,
        timezone="UTC",
        theme="system"
    )
    db.add(user)
    db.commit()
    db.close()
    
    yield
    
    # Drop tables to release constraints between tests
    Base.metadata.drop_all(bind=engine)

# Override database dependency in FastAPI app
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_password_utils():
    """Verify that bcrypt password hashing functions correctly."""
    from backend.modules.users.utils import hash_password, verify_password
    pwd = "mysecurepassword"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_pwd", hashed) is False


def test_encryption_utils():
    """Verify that config encryption and decryption works using Fernet."""
    from backend.modules.users.utils import encrypt_config, decrypt_config
    secret = app_settings.SECRET_KEY.get_secret_value()
    raw_config = '{"host": "localhost", "password": "supersecret"}'
    
    encrypted = encrypt_config(raw_config, secret)
    assert encrypted != raw_config
    
    decrypted = decrypt_config(encrypted, secret)
    assert decrypted == raw_config


def test_get_profile():
    """Test retrieving current user profile endpoint."""
    response = client.get("/api/user/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@qolyx.io"
    assert data["username"] == "admin"


def test_update_profile():
    """Test updating user profile properties."""
    update_payload = {
        "name": "Ayush Kushwah",
        "job_title": "Lead Dev",
        "timezone": "IST"
    }
    response = client.put("/api/user/profile", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ayush Kushwah"
    assert data["job_title"] == "Lead Dev"
    assert data["timezone"] == "IST"


def test_change_password_endpoint():
    """Test changing account password through the change-password route."""
    payload = {
        "old_password": "adminpassword123",
        "new_password": "newsecurepassword1"
    }
    response = client.post("/api/user/change-password", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully."

    # Failed validation (wrong old password)
    payload_fail = {
        "old_password": "wrongpassword",
        "new_password": "somepassword"
    }
    response_fail = client.post("/api/user/change-password", json=payload_fail)
    assert response_fail.status_code == 400


def test_get_active_sessions():
    """Test fetching active login sessions."""
    response = client.get("/api/user/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["is_active"] is True


def test_revoke_session():
    """Test revoking a specific user session."""
    response = client.get("/api/user/sessions")
    session_id = response.json()[0]["id"]
    
    resp_delete = client.delete(f"/api/user/sessions/{session_id}")
    assert resp_delete.status_code == 200
    
    resp_again = client.delete(f"/api/user/sessions/{session_id}")
    assert resp_again.status_code == 200


def test_app_settings_endpoints():
    """Test retrieving and saving global system settings (CORS origins, threshold, etc.)."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "cors_origins" in data
    assert "data_retention_days" in data

    update_payload = {
        "data_retention_days": 180,
        "incident_threshold": 85
    }
    response_put = client.put("/api/settings", json=update_payload)
    assert response_put.status_code == 200
    data_put = response_put.json()
    assert data_put["data_retention_days"] == 180
    assert data_put["incident_threshold"] == 85


def test_api_keys_workflow():
    """Test API key lifecycle (Generate -> List -> Revoke)."""
    payload = {"name": "CI Deployment Token", "expires_in_days": 30}
    response = client.post("/api/settings/api-keys", json=payload)
    assert response.status_code == 200
    key_data = response.json()
    assert key_data["name"] == "CI Deployment Token"
    assert "key" in key_data
    assert key_data["key"].startswith("qlx_live_")

    resp_list = client.get("/api/settings/api-keys")
    assert resp_list.status_code == 200
    keys = resp_list.json()
    assert len(keys) == 1
    assert keys[0]["name"] == "CI Deployment Token"

    key_id = keys[0]["id"]
    resp_revoke = client.delete(f"/api/settings/api-keys/{key_id}")
    assert resp_revoke.status_code == 200
    
    resp_list_after = client.get("/api/settings/api-keys")
    assert len(resp_list_after.json()) == 0


def test_integrations_workflow():
    """Test Integration Connection workflow (Save -> Test -> Sync -> Delete)."""
    payload = {
        "name": "Warehouse Analytics DB",
        "provider": "POSTGRESQL",
        "config": {
            "host": "localhost",
            "port": 5432,
            "database": "analytics",
            "username": "qolyx_dw",
            "password": "secret_db_password"
        }
    }
    response = client.post("/api/settings/integrations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Warehouse Analytics DB"
    assert data["provider"] == "POSTGRESQL"
    assert data["config_preview"]["password"] == "********"
    assert data["config_preview"]["host"] == "localhost"

    resp_test = client.post("/api/settings/integrations/test", json=payload)
    assert resp_test.status_code == 200
    assert resp_test.json()["success"] is True

    conn_id = data["id"]
    resp_sync = client.post(f"/api/settings/integrations/{conn_id}/sync")
    assert resp_sync.status_code == 200
    sync_data = resp_sync.json()
    assert "assets" in sync_data
    assert len(sync_data["assets"]) > 0

    resp_del = client.delete(f"/api/settings/integrations/{conn_id}")
    assert resp_del.status_code == 200
