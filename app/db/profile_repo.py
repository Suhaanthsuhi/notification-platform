import json
from sqlalchemy import text
from app.db.engine import AsyncSessionLocal
from core import RedisClient

CACHE_TTL_SECONDS = 600  # 10 minutes


async def get_user_by_user_id(user_id: str):
    """
    Load a user's profile, Redis-cached with a DB fallback.

    Returns a dict the enricher attaches under context["profile"], which the
    template layer reads for personalization and language resolution.
    """

    redis_client = RedisClient()
    cache_key = f"user:profile:{user_id}"

    # Try cache first
    try:
        cached = await redis_client.get_client().get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        # Never fail because Redis failed
        pass

    # Fallback to DB
    async with AsyncSessionLocal() as session:

        stmt = text("""
            SELECT first_name, last_name, language, email
            FROM users
            WHERE id = :user_id
        """)

        result = await session.execute(stmt, {"user_id": user_id})
        row = result.mappings().first()

        if not row:
            return None

        user_data = {
            "language": row["language"] or "en",
            "firstname": row["first_name"] or "there",
            "lastname": row["last_name"] or None,
            "email": row["email"],
        }

    # Store in cache
    try:
        await redis_client.get_client().set(
            cache_key,
            json.dumps(user_data),
            ex=CACHE_TTL_SECONDS,
        )
    except Exception:
        pass

    return user_data
