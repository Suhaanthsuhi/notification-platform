# core/redis_client.py
"""
Redis Infrastructure Client

This module provides an asynchronous Redis abstraction used across
the notification platform for event streaming, distributed locking,
rate limiting, and failure recovery.

It is the core infrastructure layer powering the event-driven pipeline.

Primary Responsibilities
------------------------

1. Connection Management
   - Lazy initialization of Redis connection
   - Async support using redis.asyncio
   - Configured timeouts and retry behavior
   - Production-ready settings for cloud Redis (e.g., AWS ElastiCache)

2. Redis Streams (Event Backbone)
   Implements the stream operations required for:

   RAW_STREAM        → Enricher
   ENRICHED_STREAM   → Engine
   DELIVERY_STREAM   → Delivery
   DLQ_STREAM        → Failure isolation

   Supported stream operations:
   - create_consumer_group() → Initializes consumer groups safely
   - xadd() → Publishes events
   - xreadgroup() → Consumes events with at-least-once semantics
   - xack() → Acknowledges processed messages
   - xpending_summary() → Monitors stuck/unacked messages
   - xclaim() → Recovers idle messages

3. Distributed Coordination Utilities

   Idempotency Lock:
   - set_if_not_exists()
   - Uses SET NX with TTL
   - Prevents duplicate event processing

   Throttling / Rate Limiting:
   - increment_with_ttl()
   - Atomic counter with expiration window
   - Used for user-level throttling in engine layer

Design Characteristics
----------------------

- Non-blocking and scalable (async-based)
- Supports horizontal worker scaling via consumer groups
- Enables fault tolerance and recovery
- Clean separation from business logic
- Infrastructure-agnostic (works locally and in cloud)

Architectural Importance
------------------------

This module is the backbone of the distributed system.

Without it:
- Event-driven flow would not function
- Idempotency guarantees would break
- Throttling logic would fail
- DLQ isolation would not exist
- Worker recovery would be impossible

It provides the reliability guarantees required for
a production-grade notification platform.
"""

import time
import redis.asyncio as redis
from typing import Optional, Dict, List, Tuple
from core.config import get_settings
from redis.exceptions import ResponseError

settings = get_settings()

STREAM_MAX_LENGTH = settings.redis_stream_max_length
# Default TTL for stream events (2 days in milliseconds)
STREAM_TTL_MS = settings.redis_stream_ttl_seconds * 1000

class RedisClient:
    def __init__(self):
        self.redis_url = settings.redis_url
        self._client: Optional[redis.Redis] = None

    def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                ssl_cert_reqs=None,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30,
                retry_on_timeout=True,
            )
        return self._client

    async def ping(self) -> bool:
        return await self.get_client().ping()

    async def close(self):
        if self._client:
            await self._client.close()

    async def create_consumer_group(self, stream: str, group: str, start_id: str = '0'):
        try:
            await self.get_client().xgroup_create(
                name=stream,
                groupname=group,
                id=start_id,
                mkstream=True,
            )
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def xadd(self, stream: str, data: Dict[str, str], maxlength: Optional[int] = None):
        """
        Add an entry to a Redis stream with dual trimming:

        1. MINID — drops entries older than the configured TTL (default: 2 days)
        2. MAXLEN — caps the stream to the latest N entries (default: 10,000)

        Since Redis only allows one trim strategy per XADD call, we use
        MINID on the XADD itself and follow up with an XTRIM MAXLEN to
        enforce the size cap. Whichever is more aggressive wins.

        Pass an explicit maxlength to override the default size cap.
        """
        max_len = maxlength or STREAM_MAX_LENGTH
        min_id = int(time.time() * 1000) - STREAM_TTL_MS

        # First: add entry and trim by age (MINID)
        result = await self.get_client().xadd(
            name=stream,
            fields=data,
            minid=min_id,
            approximate=True,
        )

        # Second: also enforce size cap (MAXLEN)
        await self.get_client().xtrim(
            name=stream,
            maxlen=max_len,
            approximate=True,
        )

        return result

    async def xreadgroup(self, stream: str, group: str, consumer: str, count: int = 10, block_ms: int = 5000):
        response = await self.get_client().xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )

        messages: List[Tuple[str, Dict[str, str]]] = []

        for _, entries in response:
            for message_id, fields in entries:
                messages.append((message_id, fields))

        return messages

    async def xack(self, stream: str, group: str, message_id: str):
        return await self.get_client().xack(stream, group, message_id)

    async def xtrim(self, stream: str, ttl_ms: Optional[int] = None):
        """
        Trim a stream to remove entries older than the TTL.

        Uses MINID trimming with approximate mode. Call this periodically
        on streams that may not receive frequent writes (e.g., DLQ) to
        ensure old entries are still cleaned up.
        """
        cutoff = int(time.time() * 1000) - (ttl_ms or STREAM_TTL_MS)
        return await self.get_client().xtrim(
            name=stream,
            minid=cutoff,
            approximate=True,
        )

    async def xpending_summary(self, stream: str, group: str):
        return await self.get_client().xpending(stream, group)

    async def xclaim(
            self,
            stream: str,
            group: str,
            consumer: str,
            min_idle_ms: int,
            message_ids: List[str],
    ):
        return await self.get_client().xclaim(
            stream,
            group,
            consumer,
            min_idle_time=min_idle_ms,
            message_ids=message_ids,
        )

    async def set_if_not_exists(self, key: str, value: str, ttl_seconds: int):
        return await self.get_client().set(
            name=key,
            value=value,
            ex=ttl_seconds,
            nx=True,
        )

    async def increment_with_ttl(self, key: str, ttl_seconds: int) -> int:
        client = self.get_client()

        value = await client.incr(key)

        # If key was just created, set TTL
        if value == 1:
            await client.expire(key, ttl_seconds)

        return value

__all__ = ["RedisClient"]