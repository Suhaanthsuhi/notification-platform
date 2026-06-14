"""
Inspect the contents of a Redis stream (non-destructive).

Reads the most recent entries with XRANGE and prints their decoded payloads.
Unlike a consumer-group read, this does NOT acknowledge or steal messages
from the real workers.

Usage:
    python -m scripts.consume_test_stream                 # raw stream
    python -m scripts.consume_test_stream enriched 20     # last 20 enriched events
    python -m scripts.consume_test_stream dlq             # dead letter queue
"""

import sys
import json
import asyncio

from core import RedisClient, get_settings

settings = get_settings()

STREAMS = {
    "raw": settings.redis_raw_stream,
    "enriched": settings.redis_enriched_stream,
    "delivery": settings.redis_delivery_stream,
    "dlq": settings.redis_dlq_stream,
}


async def inspect(stream: str, count: int):
    r = RedisClient()
    entries = await r.get_client().xrevrange(stream, max="+", min="-", count=count)
    await r.close()

    if not entries:
        print(f"(stream '{stream}' is empty)")
        return

    print(f"Last {len(entries)} entries of '{stream}':\n")
    for msg_id, fields in reversed(entries):
        payload = fields.get("payload")
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            pass
        print(f"--- {msg_id} ---")
        print(json.dumps({**fields, "payload": payload}, indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "raw"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    asyncio.run(inspect(STREAMS.get(key, key), n))
