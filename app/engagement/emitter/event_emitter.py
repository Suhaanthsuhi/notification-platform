# app/engagement/emitter/event_emitter.py
"""
Emit events into notification RAW stream
"""

import json
import ulid
import uuid
import logging
from datetime import datetime, timezone

from core import RedisClient, get_settings

settings = get_settings()
redis = RedisClient()

logger = logging.getLogger("ENGAGEMENT")

async def emit_event(event_name: str, user_id: str):

    event = {

        "event_id": f"eng_{uuid.uuid4()}",
        "trace_id": f"trace_{ulid.new()}",
        "event_name": event_name,
        "event_version": 1,

        "source_service": "engagement_service",
        "priority": 0,
        "environment": settings.env,

        "occurred_at": datetime.now(timezone.utc).isoformat(),

        "target": {
            "user_id": user_id,
            "topic": None,
            "broadcast": False
        },

        "data": {}
    }

    logger.info(
        "Emitting engagement event %s for user %s",
        event_name,
        user_id,
    )

    await redis.xadd(
        settings.redis_raw_stream,
        {"payload": json.dumps(event)}
    )