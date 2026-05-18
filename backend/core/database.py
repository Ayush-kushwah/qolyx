import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.core.config import settings

logger = logging.getLogger("qolyx.database")

# Ensure DATABASE_URL is converted to a string
db_url: str = str(settings.DATABASE_URL)

logger.info("Initializing SQLAlchemy database engine", extra={"pool_size": 20, "max_overflow": 40})

try:
    engine = create_engine(
        db_url,
        pool_size=20,
        max_overflow=40,
        pool_recycle=1800,
        pool_pre_ping=True
    )
except Exception as e:
    logger.error("Failed to create database engine", exc_info=True)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to retrieve the database session context."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
