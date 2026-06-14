"""
Produce a test event into the raw stream.

Publishes a well-formed event (matching the RawEvent contract) so it flows
through the full pipeline: enricher -> engine -> delivery.

Usage:
    python -m scripts.produce_test_event                       # USER_REGISTERED for user_alice
    python -m scripts.produce_test_event SUBSCRIPTION_EXPIRED user_alice
"""

import sys
import json
import uuid
import asyncio
from datetime import datetime, timezone

from core import RedisClient, get_settings

settings = get_settings()

# Per-event sample `data` payloads (must satisfy the registered schema).
SAMPLE_DATA = {
    "USER_REGISTERED": {"platform": "android", "app_version": "1.0.0"},
    "SUBSCRIPTION_EXPIRED": {"subscription_id": "sub_alice", "plan_name": "Pro"},
    "WEEKLY_REPORT_READY": {"report_id": "rpt_123", "period": "2026-W24"},
    "ALERT_API_USAGE_LIMIT_REACHED": {"subscription_id": "sub_alice", "usage": 10000},
}


async def produce(event_name: str, user_id: str):
    r = RedisClient()

    event = {
        "event_id": f"evt_{uuid.uuid4()}",
        "trace_id": f"trace_{uuid.uuid4()}",
        "event_name": event_name,
        "event_version": 1,
        "source_service": "test_producer",
        "priority": 0,
        "environment": settings.env,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "target": {"user_id": user_id, "topic": None, "broadcast": False},
        "data": SAMPLE_DATA.get(event_name, {}),
    }

    msg_id = await r.xadd(
        stream=settings.redis_raw_stream,
        data={"payload": json.dumps(event)},
    )
    await r.close()

    print(f"Produced {event_name} -> {settings.redis_raw_stream} (msg_id={msg_id})")
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "USER_REGISTERED"
    uid = sys.argv[2] if len(sys.argv) > 2 else "user_alice"
    asyncio.run(produce(name, uid))
