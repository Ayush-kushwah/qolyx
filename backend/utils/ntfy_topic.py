import logging
import uuid
from datetime import datetime, timezone

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.modules.incidents.models import SystemSettings

logger = logging.getLogger("qolyx.utils.ntfy_topic")


def get_or_create_ntfy_topic() -> str:
    """Retrieves the default Ntfy alert topic from settings or database, creating it if needed."""
    if settings.NTFY_TOPIC:
        return settings.NTFY_TOPIC

    db = None
    try:
        db = SessionLocal()
        record = db.query(SystemSettings).filter(SystemSettings.key == "ntfy_topic").first()
        if record and record.value:
            return str(record.value)

        # Generate a new randomized topic key
        new_topic = f"qolyx_alerts_{uuid.uuid4().hex[:8]}"
        new_record = SystemSettings(
            id=uuid.uuid4(),
            key="ntfy_topic",
            value=new_topic,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_record)
        db.commit()
        logger.info(f"Generated and saved new default Ntfy topic: {new_topic}")
        return new_topic
    except Exception as exc:
        logger.error(
            "Failed to retrieve or create default Ntfy topic from database. Falling back to default.",
            exc_info=True
        )
        return "qolyx_alerts_default"
    finally:
        if db is not None:
            db.close()
