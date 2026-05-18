import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Any, Dict, Optional
import redis
from pydantic import BaseModel, Field, ConfigDict
from backend.core.config import settings

logger = logging.getLogger("qolyx.events")

class QolyxEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event tracking UUID")
    event_type: str = Field(..., description="Chronological event namespace")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 formatted UTC timestamp")
    data: dict = Field(..., description="Inner payload containing dataset metadata")

# Parse Redis URL and establish a client connection
redis_url: str = str(settings.REDIS_URL)
logger.info("Establishing Redis connection", extra={"redis_url": redis_url})
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

def publish(event_type: str, payload: dict) -> None:
    """Publishes a structured event to the Redis event bus.
    
    If the payload is not wrapped in the standard event envelope,
    it automatically constructs the QolyxEvent metadata structure.
    """
    try:
        # Check if the payload is already enveloped
        if all(k in payload for k in ("event_id", "event_type", "timestamp", "data")):
            event = QolyxEvent(**payload)
        else:
            event = QolyxEvent(
                event_type=event_type,
                data=payload
            )
            
        event_json = event.model_dump_json()
        
        logger.info(
            "Publishing event to Redis bus",
            extra={
                "event_type": event.event_type,
                "event_id": event.event_id,
                "channel": event.event_type
            }
        )
        
        redis_client.publish(event.event_type, event_json)
        
    except Exception as exc:
        logger.error(
            "Failed to publish event to Redis bus",
            exc_info=True,
            extra={"event_type": event_type}
        )
        raise

def subscribe(event_type: str, handler: Callable[[dict], None]) -> Any:
    """Subscribes a callable handler to a specific event type channel.
    
    Runs a non-blocking background subscription loop inside a daemon thread.
    Returns the thread handle which can be stopped using thread.stop().
    """
    logger.info("Registering subscriber handler", extra={"channel": event_type})
    
    pubsub = redis_client.pubsub()
    
    def message_handler(message: dict) -> None:
        try:
            data_str = message.get("data")
            if not data_str:
                return
            
            event_payload = json.loads(data_str)
            logger.debug(
                "Event bus subscriber received message",
                extra={
                    "channel": event_type,
                    "event_id": event_payload.get("event_id")
                }
            )
            handler(event_payload)
        except Exception as exc:
            logger.error(
                "Error processing event inside subscriber callback",
                exc_info=True,
                extra={"channel": event_type}
            )
            
    pubsub.subscribe(**{event_type: message_handler})
    # Spawn background daemon listener thread
    thread = pubsub.run_in_thread(sleep_time=0.1, daemon=True)
    logger.info("Event subscriber background thread started", extra={"channel": event_type})
    return thread
