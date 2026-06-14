import json
from sqlalchemy import text
from app.db.engine import AsyncSessionLocal
from typing import List, Tuple
from core import RedisClient

CACHE_TTL_SECONDS = 600  # 10 minutes

redis_client = RedisClient()  # reuse client


async def get_tokens_from_user_id(user_id: str):
    """
    Return active device tokens for a user, Redis-cached with a DB fallback.
    Keeps the delivery hot path fast while staying consistent with the DB.
    """

    cache_key = f"user:notification:tokens:{user_id}"

    # Try cache first
    try:
        cached = await redis_client.get_client().get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # Redis failure should not break the system

    # Fallback to DB
    async with AsyncSessionLocal() as session:

        stmt = text("""
            SELECT user_id, device_id, token, platform
            FROM device_tokens
            WHERE user_id = :user_id
              AND active = TRUE
        """)

        result = await session.execute(stmt, {"user_id": user_id})
        rows = result.mappings().all()

        data = [
            {
                "user_id": row["user_id"],
                "device_id": row["device_id"],
                "token": row["token"],
                "platform": row["platform"],
            }
            for row in rows
        ]

        # Store in cache
        try:
            await redis_client.get_client().set(
                cache_key,
                json.dumps(data),
                ex=CACHE_TTL_SECONDS,
            )
        except Exception:
            pass

        return data


async def deactivate_user_devices(devices: List[Tuple[str, str]]):
    """
    Mark device tokens inactive (e.g. after FCM reports them invalid) and
    invalidate the per-user token cache so the next read is consistent.
    """

    if not devices:
        return

    async with AsyncSessionLocal() as session:

        stmt = text("""
            UPDATE device_tokens
            SET active = FALSE,
                last_failure_reason = :reason,
                updated_at = NOW()
            WHERE user_id = :user_id
              AND device_id = :device_id
        """)

        for user_id, device_id in devices:
            await session.execute(
                stmt,
                {
                    "user_id": user_id,
                    "device_id": device_id,
                    "reason": "INVALID_FCM_TOKEN",
                },
            )

        await session.commit()

    # Invalidate cache
    unique_users = {user_id for user_id, _ in devices}

    for user_id in unique_users:
        cache_key = f"user:notification:tokens:{user_id}"
        try:
            await redis_client.get_client().delete(cache_key)
        except Exception:
            pass
