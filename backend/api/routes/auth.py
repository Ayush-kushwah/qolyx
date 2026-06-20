import logging
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import settings
from backend.modules.users.models import User, UserSession, LoginHistory
from backend.modules.users.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserProfileResponse,
)
from backend.modules.users.utils import hash_password, verify_password

logger = logging.getLogger("qolyx.api.routes.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserProfileResponse)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new platform user."""
    logger.info(f"Attempting registration for email: {payload.email}")

    # Check if email exists
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Check if username exists
    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username already exists."
        )

    # Create new user
    hashed = hash_password(payload.password)
    new_user = User(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email,
        username=payload.username,
        hashed_password=hashed,
        timezone="UTC",
        theme="system",
        date_format="ISO",
        notification_preferences={
            "email": True,
            "slack": True,
            "telegram": False,
            "severity": "MEDIUM",
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00"
            }
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Successfully registered user: {new_user.email}")
    return new_user

@router.post("/login")
def login(payload: UserLoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    """Authenticate credentials, log session and return JWT session cookie."""
    logger.info(f"Authentication attempt: {payload.email}")

    user = db.query(User).filter(User.email == payload.email).first()
    
    # IP and User Agent extraction for security audit logging
    ip_addr = request.client.host if request.client else "Unknown"
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Parse browser/device from user agent simply
    device = "Unknown Device"
    browser = "Unknown Browser"
    if "Macintosh" in user_agent:
        device = "macOS Device"
    elif "Windows" in user_agent:
        device = "Windows PC"
    elif "iPhone" in user_agent:
        device = "iPhone"
    elif "Android" in user_agent:
        device = "Android Device"
        
    if "Chrome" in user_agent:
        browser = "Chrome"
    elif "Safari" in user_agent:
        browser = "Safari"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Edge" in user_agent:
        browser = "Edge"

    if not user or not verify_password(payload.password, user.hashed_password):
        if user:
            # Log failure
            fail_log = LoginHistory(
                id=uuid.uuid4(),
                user_id=user.id,
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_addr,
                location="Remote Ingress",
                device=device,
                browser=browser,
                success=False
            )
            db.add(fail_log)
            db.commit()
            
        logger.warning(f"Failed authentication attempt for email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    # 1. Create UserSession
    new_session = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        device=device,
        browser=browser,
        ip_address=ip_addr,
        location="Remote Ingress",
        last_active_at=datetime.now(timezone.utc),
        is_active=True
    )
    db.add(new_session)

    # 2. Create LoginHistory log
    success_log = LoginHistory(
        id=uuid.uuid4(),
        user_id=user.id,
        timestamp=datetime.now(timezone.utc),
        ip_address=ip_addr,
        location="Remote Ingress",
        device=device,
        browser=browser,
        success=True
    )
    db.add(success_log)
    
    db.commit()
    db.refresh(new_session)

    # 3. Generate JWT Token
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES or 1440)
    token_payload = {
        "user_id": str(user.id),
        "email": user.email,
        "session_id": str(new_session.id),
        "exp": int(expiry.timestamp())
    }
    
    token = jwt.encode(
        token_payload, 
        settings.SECRET_KEY.get_secret_value(), 
        algorithm=settings.JWT_ALGORITHM or "HS256"
    )

    # 4. Set Session Cookie (httpOnly, samesite strict for CSRF protection)
    response.set_cookie(
        key="qolyx_session",
        value=token,
        httponly=True,
        max_age=3600 * 24, # 24 hours
        expires=int(expiry.timestamp()),
        samesite="lax", # Lax matches frontend/backend domain dev layouts
        secure=settings.ENVIRONMENT == "production"
    )

    logger.info(f"Successful login: {user.email}, session_id: {new_session.id}")
    return {
        "message": "Login successful",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "username": user.username,
        }
    }

@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    """Revoke user session and delete cookie."""
    token = request.cookies.get("qolyx_session")
    if token:
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY.get_secret_value(), 
                algorithms=[settings.JWT_ALGORITHM or "HS256"]
            )
            session_id = payload.get("session_id")
            if session_id:
                try:
                    session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
                except ValueError:
                    session_uuid = session_id
                session = db.query(UserSession).filter(UserSession.id == session_uuid).first()
                if session:
                    session.is_active = False
                    db.commit()
                    logger.info(f"Deactivated session: {session_id} on logout.")
        except Exception as e:
            logger.warning(f"Error reading session token during logout: {e}")

    # Delete the cookie
    response.delete_cookie(
        key="qolyx_session",
        samesite="lax",
        secure=settings.ENVIRONMENT == "production"
    )
    return {"message": "Logged out successfully"}
