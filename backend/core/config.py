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
    
    # External APIs
    FINNHUB_API_KEY: Optional[str] = None
    ANOMALY_DECAY_FACTOR: float = 0.95

    # Airflow configuration keys
    AIRFLOW_FERNET_KEY: str = ""
    AIRFLOW_SECRET_KEY: str = ""

    # JWT configuration
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # Database Pool configurations
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # SMTP configurations
    SMTP_SERVER: str = "qolyx-mail"
    SMTP_PORT: int = 1025

    # Additional Airflow settings
    AIRFLOW_UID: int = 50000
    AIRFLOW_GID: int = 0
    AIRFLOW__CORE__EXECUTOR: str = "LocalExecutor"

    # dbt Configuration
    DBT_HOST: str = "qolyx-db"
    DBT_USER: str = ""
    DBT_PASSWORD: str = ""
    DBT_PORT: int = 5432
    DBT_DBNAME: str = ""
    DBT_TARGET: str = "dev"


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
