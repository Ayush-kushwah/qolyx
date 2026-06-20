import pytest
import uuid
import jwt
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.core.database import Base, get_db
from backend.core.config import settings
from backend.modules.users.models import User, UserSession, LoginHistory

# In-memory SQLite for testing auth
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_overrides():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_auth_workflow():
    # 1. Register User
    reg_payload = {
        "name": "Operator Test",
        "email": "operator@qolyx.io",
        "username": "operator",
        "password": "securepassword123"
    }
    response_reg = client.post("/api/auth/register", json=reg_payload)
    assert response_reg.status_code == 200
    reg_data = response_reg.json()
    assert reg_data["email"] == "operator@qolyx.io"
    assert reg_data["username"] == "operator"
    
    # 2. Login Failure (Wrong password)
    login_fail_payload = {
        "email": "operator@qolyx.io",
        "password": "wrongpassword"
    }
    response_fail = client.post("/api/auth/login", json=login_fail_payload)
    assert response_fail.status_code == 401
    
    db = TestingSessionLocal()
    login_fails = db.query(LoginHistory).filter(LoginHistory.success == False).all()
    assert len(login_fails) == 1
    db.close()

    # 3. Login Success
    login_payload = {
        "email": "operator@qolyx.io",
        "password": "securepassword123"
    }
    response_login = client.post("/api/auth/login", json=login_payload)
    assert response_login.status_code == 200
    assert "qolyx_session" in response_login.cookies
    
    session_token = response_login.cookies["qolyx_session"]
    
    # 4. Verify Route Protection & Session Access
    # (FastAPI testclient automatically sends cookies received in preceding responses)
    # So we call user profile route
    response_prof = client.get("/api/user/profile")
    assert response_prof.status_code == 200
    prof_data = response_prof.json()
    assert prof_data["email"] == "operator@qolyx.io"
    
    # Check session in DB
    db = TestingSessionLocal()
    session = db.query(UserSession).filter(UserSession.is_active == True).first()
    assert session is not None
    assert str(session.user_id) == reg_data["id"]
    db.close()

    # 5. Logout
    response_logout = client.post("/api/auth/logout")
    assert response_logout.status_code == 200
    
    # Cookie should be deleted/cleared
    # Note: TestClient cookies are maintained in client.cookies
    assert "qolyx_session" not in client.cookies or client.cookies["qolyx_session"] == ""
    
    # Check session deactivated
    db = TestingSessionLocal()
    session_deactivated = db.query(UserSession).filter(UserSession.is_active == False).first()
    assert session_deactivated is not None
    db.close()

    # 6. Profile access should now be blocked
    # Explicitly clear client cookies to simulate unauthenticated client
    client.cookies.clear()
    response_prof_blocked = client.get("/api/user/profile")
    assert response_prof_blocked.status_code == 401
