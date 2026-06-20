import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from backend.main import app
from backend.core.database import Base, get_db
from backend.core.config import settings
from backend.modules.users.models import User, LLMProvider
from backend.modules.users.utils import decrypt_config

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    # Seed default user
    from backend.modules.users.utils import hash_password
    user = User(
        id=uuid.uuid4(),
        name="Administrator",
        email="admin@qolyx.io",
        username="admin",
        hashed_password=hash_password("adminpassword123"),
        timezone="UTC",
        theme="system"
    )
    db.add(user)
    db.commit()
    db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

from backend.api.routes.users import get_current_user
def override_get_current_user():
    # Bypass auth for LLM CRUD tests specifically using mock dependency injection
    db = TestingSessionLocal()
    try:
        return db.query(User).filter(User.email == "admin@qolyx.io").first()
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_llm_provider_crud():
    # 1. Create Provider
    payload = {
        "name": "Ollama In-House",
        "provider_type": "OLLAMA",
        "base_url": "http://localhost:11434/v1",
        "model_name": "llama3.2",
        "api_key": "mysecretkey123",
        "is_active": True,
        "priority": 1
    }
    response = client.post("/api/llm/providers", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ollama In-House"
    assert data["provider_type"] == "OLLAMA"
    assert "api_key" not in data  # Key should never leak in response schemas!

    # Check key is encrypted in db
    db = TestingSessionLocal()
    db_provider = db.query(LLMProvider).filter(LLMProvider.name == "Ollama In-House").first()
    assert db_provider is not None
    assert db_provider.encrypted_api_key != "mysecretkey123"
    
    # Decrypt and verify
    decrypted = decrypt_config(db_provider.encrypted_api_key, settings.SECRET_KEY.get_secret_value())
    assert decrypted == "mysecretkey123"
    db.close()

    # 2. Get list of providers
    response_list = client.get("/api/llm/providers")
    assert response_list.status_code == 200
    providers_list = response_list.json()
    assert len(providers_list) == 1
    assert providers_list[0]["name"] == "Ollama In-House"

    # 3. Update Provider
    update_payload = {
        "name": "Ollama Production",
        "provider_type": "OLLAMA",
        "base_url": "http://localhost:11434/v1",
        "model_name": "llama3.2-instruct",
        "api_key": "new_key",
        "is_active": True,
        "priority": 0
    }
    provider_id = data["id"]
    response_put = client.put(f"/api/llm/providers/{provider_id}", json=update_payload)
    assert response_put.status_code == 200
    assert response_put.json()["name"] == "Ollama Production"
    assert response_put.json()["model_name"] == "llama3.2-instruct"

    # 4. Test provider connectivity (Mocked)
    test_payload = {
        "provider_type": "OLLAMA",
        "base_url": "http://localhost:11434/v1",
        "model_name": "llama3.2-instruct",
        "api_key": "test"
    }
    
    with patch("backend.api.routes.llm.execute_llm_chat") as mock_chat:
        mock_chat.return_value = "OK"
        response_test = client.post("/api/llm/providers/test", json=test_payload)
        assert response_test.status_code == 200
        assert response_test.json()["success"] is True
        assert response_test.json()["response_preview"] == "OK"

    # 5. Delete Provider
    response_del = client.delete(f"/api/llm/providers/{provider_id}")
    assert response_del.status_code == 200
    
    response_list_empty = client.get("/api/llm/providers")
    assert len(response_list_empty.json()) == 0
