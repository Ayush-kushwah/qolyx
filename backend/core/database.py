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
    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            pool_recycle=1800,
            pool_pre_ping=True
        )
        import os
        from sqlalchemy import event
        # database.py is in backend/core/database.py, so root is two levels up
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        public_silver_path = os.path.join(workspace_root, "public_silver.db")
        test_results_path = os.path.join(workspace_root, "test_results.db")
        
        @event.listens_for(engine, "connect")
        def connect(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute(f"ATTACH DATABASE '{public_silver_path.replace(chr(92), chr(47))}' AS public_silver")
            cursor.execute(f"ATTACH DATABASE '{test_results_path.replace(chr(92), chr(47))}' AS test_results")
            cursor.close()
    else:
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
