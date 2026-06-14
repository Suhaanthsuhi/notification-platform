# core/utils.py
"""
Utility Module

This module defines all the utility functions, that can be used by this entire repo.
Like Logging, etc
"""

import logging
import logging.config
import uuid
import ulid
from core.config import get_settings
from datetime import datetime, timezone
from core.redis_client import RedisClient
import json

settings = get_settings()
redis_client = RedisClient()

def setup_logging():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "[%(name)s] %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["stdout"],
        },
    }

    logging.config.dictConfig(logging_config)

def generate_event_id():
    event_id = f"evt_{uuid.uuid4()}"
    return event_id

def generate_trace_id():
    trace_id = f"trace_{ulid.new()}"
    return trace_id

async def publish_event(event_id: str, event_name: str, user_id: str):
    event_payload = {
        "event_id": event_id,
        "event_name": event_name,
        "trace_id": generate_trace_id(),
        "event_version": 1,
        "source_service": f"Notification-Engagement",
        "priority": 0,
        "environment": settings.env,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "user_id": user_id,
        },
        "data": {}
    }

    print(event_payload)

    await redis_client.xadd(
        stream=settings.redis_raw_stream,
        data={"payload": json.dumps(event_payload)},
    )