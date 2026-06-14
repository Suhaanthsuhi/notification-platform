# app/engine/decision/throttling.py
"""
Throttling Module

This module implements user-level rate limiting for notifications.

It prevents excessive notifications from being sent to a single user
within a defined time window by leveraging Redis atomic counters with TTL.

Mechanism:
- Each user has a Redis key: throttle:user:<user_id>
- Every notification attempt increments the counter
- The key automatically expires after THROTTLE_WINDOW_SECONDS
- If the counter exceeds THROTTLE_LIMIT within the window,
  the user is considered throttled

This approach ensures:
- Simple and efficient rate limiting
- Atomic increments (safe under concurrency)
- Automatic reset after time window
- No additional cleanup logic required

It acts as a protective layer against spam, abuse,
and accidental notification floods.
"""

from core import get_settings
from core import RedisClient

settings = get_settings()

THROTTLE_LIMIT = 3
THROTTLE_WINDOW_SECONDS = 3600

async def is_throttled(r: RedisClient, user_id: str) -> bool:

    key = f"throttle:user:{user_id}"

    # increment count
    count = await r.increment_with_ttl(
        key=key,
        ttl_seconds=THROTTLE_WINDOW_SECONDS,
    )

    if count > THROTTLE_LIMIT:
        return True

    return False