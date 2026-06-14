# app/engagement/cooldown/cooldown_manager.py
"""
Cooldown Manager
Prevents repeated notifications
"""

from core import RedisClient

redis = RedisClient()


async def is_on_cooldown(user_id: str, event_name: str):

    key = f"notif:cooldown:{user_id}:{event_name}"

    return await redis.get_client().get(key)


async def set_cooldown(user_id: str, event_name: str, days: int):

    key = f"notif:cooldown:{user_id}:{event_name}"

    await redis.get_client().set(
        key,
        "1",
        ex=days * 24 * 3600,
    )