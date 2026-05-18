from typing import Literal, Optional
from pydantic import AnyUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core system settings
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: SecretStr
    
    # Network parameters (strict type checks)
    BACKEND_PORT: int = 8000
    POSTGRES_PORT: int = 5432
    REDIS_PORT: int = 6379
    FRONTEND_PORT: int = 5173
    AIRFLOW_PORT: int = 8080
    MAIL_UI_PORT: int = 8025
    MAIL_SMTP_PORT: int = 1025
    PROMETHEUS_PORT: int = 9090
    GRAFANA_PORT: int = 3000

    # Database & Cache Broker Info
    POSTGRES_USER: str = "qolyx_admin"
    POSTGRES_PASSWORD: str = "postgres_secure_pass"
    POSTGRES_DB: str = "qolyx_prod"
    POSTGRES_HOST: str = "qolyx-db"
    REDIS_HOST: str = "qolyx-cache"

    # Storage URLs
    DATABASE_URL: AnyUrl
    REDIS_URL: AnyUrl

    # Alert bindings
    ALERT_EMAIL_SENDER: str = "alerts@qolyx.ai"
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Load parameters strictly from file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid"  # Strictly bans undocumented variables to prevent naming drift
    )

    @field_validator("DATABASE_URL")
    def validate_postgres_protocol(cls, v: AnyUrl) -> AnyUrl:
        if v.scheme != "postgresql":
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection scheme.")
        return v

# Singleton instantiation
settings = Settings()
