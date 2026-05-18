import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from backend.core.config import settings

class JSONFormatter(logging.Formatter):
    """Formatter that converts log records to JSON format for structured logs."""
    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        
        # Capture traceback details if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
            
        # Capture custom extra parameters passed via the 'extra' dict
        standard_fields = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process"
        }
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                log_payload[key] = value
                
        return json.dumps(log_payload)

def setup_logging() -> None:
    """Configures structured JSON logging for the 'qolyx' logger namespace."""
    logger = logging.getLogger("qolyx")
    
    # Determine the log level based on ENVIRONMENT
    if settings.ENVIRONMENT in ("production", "staging"):
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG
        
    logger.setLevel(log_level)
    
    # Clear existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Configure StreamHandler for standard output
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Prevent propagation to the root logger
    logger.propagate = False
    
    logger.info(
        "Structured JSON logging initialized", 
        extra={"environment": settings.ENVIRONMENT, "level": logging.getLevelName(log_level)}
    )

# Execute setup on import
setup_logging()
