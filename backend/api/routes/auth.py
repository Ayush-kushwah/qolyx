import logging
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import settings
from backend.core.events import redis_client
from backend.modules.users.models import User, UserSession, LoginHistory, EmailVerification
from backend.modules.users.email_utils import send_verification_email
from email_validator import validate_email, EmailNotValidError
import random
import re
from pydantic import BaseModel
from backend.modules.users.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserProfileResponse,
)
from backend.modules.users.utils import hash_password, verify_password

logger = logging.getLogger("qolyx.api.routes.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new platform user with validation and OTP generation."""
    logger.info(f"Attempting registration for email: {payload.email}")

    # 1. Validate email format using email-validator
    try:
        validation = validate_email(payload.email, check_deliverability=False)
        payload.email = validation.normalized
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email format: {str(e)}"
        )

    # 2. Check if email exists
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        if existing_email.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )
        else:
            logger.info(f"Deleting inactive unverified user {existing_email.email} for re-registration.")
            db.delete(existing_email)
            db.commit()

    # 3. Check if username exists
    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        if existing_username.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists."
            )
        else:
            logger.info(f"Deleting inactive unverified user with username {existing_username.username} for re-registration.")
            db.delete(existing_username)
            db.commit()

    # 4. Password strength validation (min 8 chars, uppercase, lowercase, number)
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", payload.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", payload.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one lowercase letter.")
    if not re.search(r"\d", payload.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one number.")

    # 5. Create inactive user
    hashed = hash_password(payload.password)
    new_user = User(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email,
        username=payload.username,
        hashed_password=hashed,
        is_active=False,  # inactive until verified
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
    db.flush()

    # 6. Generate 6-digit verification code
    verification_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    verification = EmailVerification(
        id=uuid.uuid4(),
        user_id=new_user.id,
        email=payload.email,
        verification_code=verification_code,
        verified=False,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(verification)
    db.commit()

    # 7. Check if SMTP is configured (SaaS Mode) vs Self-Hosted Mode
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        # Self-hosted mode with no SMTP -> auto-verify
        new_user.is_active = True
        verification.verified = True
        db.commit()
        logger.info(f"Self-hosted instance auto-verified user {new_user.email}")
        return {
            "message": "Account created successfully. (Email verification skipped — self-hosted mode.)",
            "user_id": str(new_user.id),
            "email": new_user.email,
            "auto_verified": True
        }
    else:
        # Dispatch verification code via SMTP
        if send_verification_email(payload.email, verification_code):
            logger.info(f"Verification email successfully sent to {new_user.email}")
            return {
                "message": "Verification email sent. Please check your inbox.",
                "user_id": str(new_user.id),
                "email": new_user.email,
                "auto_verified": False
            }
        else:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please check SMTP configuration."
            )


class VerifyEmailRequest(BaseModel):
    user_id: str
    code: str


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verifies a user's email address using the 6-digit OTP code with rate limiting."""
    # Rate limit attempts per user to prevent brute-forcing OTP
    rate_limit_key = f"rate_limit:verify_email:{payload.user_id}"
    attempts = redis_client.get(rate_limit_key)
    
    if attempts and int(attempts) >= 5:
        logger.warning(f"Rate limit exceeded for OTP verification on user_id: {payload.user_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again in 15 minutes."
        )
        
    # Increment the attempts count
    try:
        pipe = redis_client.pipeline()
        pipe.incr(rate_limit_key)
        if not attempts:
            pipe.expire(rate_limit_key, 900)  # 15 minutes TTL
        pipe.execute()
    except Exception as redis_err:
        logger.warning(f"Failed to record rate limit attempt in Redis: {redis_err}")

    # Find verification record
    verification = db.query(EmailVerification).filter(
        EmailVerification.user_id == uuid.UUID(payload.user_id),
        EmailVerification.verification_code == payload.code,
        EmailVerification.verified == False
    ).first()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or user ID."
        )

    # Convert expires_at to timezone-aware UTC if it is naive
    expires_at_aware = verification.expires_at
    if expires_at_aware.tzinfo is None:
        expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)

    if expires_at_aware < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired."
        )

    # Activate user
    user = db.query(User).filter(User.id == verification.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    user.is_active = True
    verification.verified = True
    db.commit()

    # Clear rate limit key on successful verification
    try:
        redis_client.delete(rate_limit_key)
    except Exception as redis_err:
        logger.warning(f"Failed to clear Redis verification rate limit: {redis_err}")

    logger.info(f"Successfully verified email and activated user: {user.email}")
    return {"message": "Email verified successfully. You can now log in."}


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

    if not user.is_active:
        logger.warning(f"Unverified login attempt for email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email before logging in. Check your inbox for the verification code."
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
        expires=expiry,
        samesite="lax", # Lax matches frontend/backend domain dev layouts
        secure=settings.ENVIRONMENT == "production",
        path="/"
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
        secure=settings.ENVIRONMENT == "production",
        path="/"
    )
    return {"message": "Logged out successfully"}
