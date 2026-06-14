import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure structured logging is configured
from backend.core import logging as _logging
from backend.core.config import settings
from backend.api.routes import health, contracts, anomaly, trust_score, incidents, users, settings as settings_route, lineage
from backend.scheduler import start_scheduler, shutdown_scheduler

logger = logging.getLogger("qolyx.main")


def seed_default_alert_config() -> None:
    """Seeds the default alert configurations on startup if they don't exist."""
    import uuid
    from datetime import datetime, timezone
    from backend.core.database import SessionLocal
    from backend.modules.incidents.models import AlertConfig
    from backend.core.config import settings

    db = SessionLocal()
    try:
        # 1. Ntfy Default
        exists_ntfy = db.query(AlertConfig).filter(AlertConfig.channel_type == "ntfy").first()
        if not exists_ntfy:
            logger.info("Seeding default Ntfy alert configuration...")
            default_config = AlertConfig(
                id=uuid.uuid4(),
                name="Ntfy Default",
                channel_type="ntfy",
                webhook_url=None,
                email_config=None,
                telegram_bot_token=None,
                telegram_chat_id=None,
                severity_threshold="MEDIUM",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(default_config)
            logger.info("Default Ntfy alert configuration successfully queued.")

        # 2. Email Default
        if settings.SMTP_HOST and settings.SMTP_HOST.strip():
            exists_email = db.query(AlertConfig).filter(AlertConfig.channel_type == "email").first()
            if not exists_email:
                logger.info("Seeding default Email alert configuration...")
                email_config = AlertConfig(
                    id=uuid.uuid4(),
                    name="Email Default",
                    channel_type="email",
                    webhook_url=None,
                    email_config={
                        "smtp_server": settings.SMTP_HOST,
                        "smtp_port": settings.SMTP_PORT or 587,
                        "smtp_user": settings.SMTP_USER,
                        "smtp_password": settings.SMTP_PASSWORD,
                        "from_address": settings.ALERT_EMAIL_FROM or settings.ALERT_EMAIL_SENDER or "alerts@qolyx.io",
                        "to_addresses": settings.ALERT_EMAIL_TO or "oncall@qolyx.io"
                    },
                    telegram_bot_token=None,
                    telegram_chat_id=None,
                    severity_threshold="MEDIUM",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(email_config)
                logger.info("Default Email alert configuration successfully queued.")

        # 3. Slack Default
        if settings.SLACK_WEBHOOK_URL and settings.SLACK_WEBHOOK_URL.strip():
            exists_slack = db.query(AlertConfig).filter(AlertConfig.channel_type == "slack").first()
            if not exists_slack:
                logger.info("Seeding default Slack alert configuration...")
                slack_config = AlertConfig(
                    id=uuid.uuid4(),
                    name="Slack Default",
                    channel_type="slack",
                    webhook_url=settings.SLACK_WEBHOOK_URL,
                    email_config=None,
                    telegram_bot_token=None,
                    telegram_chat_id=None,
                    severity_threshold="MEDIUM",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(slack_config)
                logger.info("Default Slack alert configuration successfully queued.")

        # 4. Discord Default
        if settings.DISCORD_WEBHOOK_URL and settings.DISCORD_WEBHOOK_URL.strip():
            exists_discord = db.query(AlertConfig).filter(AlertConfig.channel_type == "discord").first()
            if not exists_discord:
                logger.info("Seeding default Discord alert configuration...")
                discord_config = AlertConfig(
                    id=uuid.uuid4(),
                    name="Discord Default",
                    channel_type="discord",
                    webhook_url=settings.DISCORD_WEBHOOK_URL,
                    email_config=None,
                    telegram_bot_token=None,
                    telegram_chat_id=None,
                    severity_threshold="MEDIUM",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(discord_config)
                logger.info("Default Discord alert configuration successfully queued.")

        # 5. Telegram Default
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN.strip():
            exists_telegram = db.query(AlertConfig).filter(AlertConfig.channel_type == "telegram").first()
            if not exists_telegram:
                logger.info("Seeding default Telegram alert configuration...")
                telegram_config = AlertConfig(
                    id=uuid.uuid4(),
                    name="Telegram Default",
                    channel_type="telegram",
                    webhook_url=None,
                    email_config=None,
                    telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
                    telegram_chat_id=settings.TELEGRAM_CHAT_ID,
                    severity_threshold="MEDIUM",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(telegram_config)
                logger.info("Default Telegram alert configuration successfully queued.")

        db.commit()
        logger.info("Alert configurations check/seeding finished.")
    except Exception as exc:
        db.rollback()
        logger.error("Failed to seed default alert configurations", exc_info=True)
    finally:
        db.close()


def seed_default_user() -> None:
    """Seeds the default administrator account if they don't exist."""
    import uuid
    from datetime import datetime, timezone
    from backend.core.database import SessionLocal
    from backend.modules.users.models import User
    from backend.modules.users.utils import hash_password

    db = SessionLocal()
    try:
        exists_user = db.query(User).filter(User.email == "admin@qolyx.io").first()
        if not exists_user:
            logger.info("Seeding default administrator user...")
            hashed = hash_password("adminpassword123")
            admin_user = User(
                id=uuid.uuid4(),
                name="Administrator",
                email="admin@qolyx.io",
                username="admin",
                hashed_password=hashed,
                avatar_url=None,
                job_title="Lead Data Reliability Engineer",
                department="Platform Engineering",
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
            db.add(admin_user)
            db.commit()
            logger.info("Default administrator user successfully seeded.")
        else:
            logger.info("Default administrator user already exists.")
    except Exception as exc:
        db.rollback()
        logger.error("Failed to seed default administrator user", exc_info=True)
    finally:
        db.close()


async def run_auto_lineage_sync():
    import asyncio
    from backend.core.database import SessionLocal
    from backend.modules.lineage.lineage_parser import sync_all_lineage
    
    logger.info("Auto-lineage sync background task starting in 5 seconds...")
    await asyncio.sleep(5)
    
    db = SessionLocal()
    try:
        logger.info("Executing auto-lineage sync...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sync_all_lineage, db)
        db.commit()
        logger.info("Auto-lineage sync completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Auto-lineage sync failed: {e}", exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info(
        "Initializing Qolyx REST Engine application lifespan",
        extra={"status": "starting", "environment": settings.ENVIRONMENT},
    )
    seed_default_alert_config()
    seed_default_user()
    start_scheduler()
    import asyncio
    asyncio.create_task(run_auto_lineage_sync())
    yield
    # Shutdown tasks
    logger.info(
        "Tearing down Qolyx REST Engine application lifespan",
        extra={"status": "stopping"},
    )
    shutdown_scheduler()


from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Qolyx API",
    description="REST Engine Ingress serving JSON APIs and health gates.",
    version="1.0.0",
    lifespan=lifespan,
)

os.makedirs("backend/static/avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# CORS configuration targeting standard client ports dynamically
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    f"http://localhost:{settings.BACKEND_PORT}",
    f"http://127.0.0.1:{settings.BACKEND_PORT}",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints under canonical prefix /api
app.include_router(health.router, prefix="/api")
app.include_router(contracts.router, prefix="/api")
app.include_router(anomaly.router, prefix="/api")
app.include_router(trust_score.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(settings_route.router, prefix="/api")
app.include_router(lineage.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Welcome to Qolyx API Ingress Engine."}
