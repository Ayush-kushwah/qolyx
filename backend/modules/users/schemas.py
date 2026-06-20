from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class NotificationPreferences(BaseModel):
    email: bool = True
    slack: bool = True
    telegram: bool = False
    severity: str = "MEDIUM"
    quiet_hours: Optional[Dict[str, Any]] = None

class UserProfileResponse(BaseModel):
    id: UUID
    name: str
    email: str
    username: str
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    timezone: str = "UTC"
    theme: str = "system"
    date_format: str = "ISO"
    notification_preferences: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    date_format: Optional[str] = None
    notification_preferences: Optional[Dict[str, Any]] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

class UserSessionResponse(BaseModel):
    id: UUID
    device: Optional[str] = None
    browser: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    last_active_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class LoginHistoryResponse(BaseModel):
    id: UUID
    timestamp: datetime
    ip_address: Optional[str] = None
    location: Optional[str] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    success: bool

    class Config:
        from_attributes = True

class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    username: str
    password: str = Field(..., min_length=8)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
