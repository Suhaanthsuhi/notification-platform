"""
Subscription / Segment Repository

Each function resolves one user segment used by the engagement campaigns.
Results are Redis-cached (segments are recomputed at most once per TTL) with
a PostgreSQL fallback.

The queries target the generic demo schema in `db/schema.sql`. Adapt the
table/column names to your own data model.
"""

import json
from sqlalchemy import text
from app.db.engine import AsyncSessionLocal
from core import RedisClient

CACHE_TTL_SECONDS = 600  # 10 minutes

# Subscription statuses considered "live" for usage-based segments.
LIVE_STATUSES = "('ACTIVE', 'TRIAL', 'FREE', 'ACTIVE_CANCELLED', 'PAUSED')"


async def _get_cached(redis_client, cache_key):
    try:
        cached = await redis_client.get_client().get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


async def _set_cache(redis_client, cache_key, data):
    try:
        await redis_client.get_client().set(
            cache_key,
            json.dumps(data),
            ex=CACHE_TTL_SECONDS,
        )
    except Exception:
        pass


async def _run_segment(cache_key: str, stmt, params: dict | None = None):
    """Cache-aside helper: return cached IDs or run the query and cache it."""
    redis_client = RedisClient()

    cached = await _get_cached(redis_client, cache_key)
    if cached is not None:
        return cached

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(stmt), params or {})
        user_ids = list(result.scalars().all())

    await _set_cache(redis_client, cache_key, user_ids)
    return user_ids


# ---------------------------------------------------------
# ALL ACTIVE USERS (anyone with a live device token)
# ---------------------------------------------------------
async def fetch_all_users():
    return await _run_segment(
        "segment:all_users",
        """
        SELECT DISTINCT user_id
        FROM device_tokens
        WHERE active = TRUE
        """,
    )


# ---------------------------------------------------------
# USERS WITHOUT A SUBSCRIPTION
# ---------------------------------------------------------
async def fetch_users_without_subscription():
    return await _run_segment(
        "segment:users_without_subscription",
        """
        SELECT u.id
        FROM users u
        LEFT JOIN subscriptions s
          ON u.id = s.user_id
          AND s.status IN ('ACTIVE', 'TRIAL')
        WHERE s.user_id IS NULL
        """,
    )


# ---------------------------------------------------------
# USERS WITH AN ACTIVE SUBSCRIPTION
# ---------------------------------------------------------
async def fetch_users_with_active_subscription():
    return await _run_segment(
        "segment:users_with_active_subscription",
        """
        SELECT DISTINCT s.user_id
        FROM subscriptions s
        WHERE s.status IN ('ACTIVE', 'TRIAL')
        """,
    )


# ---------------------------------------------------------
# NEWLY SUBSCRIBED USERS (within the last N days)
# ---------------------------------------------------------
async def fetch_users_with_new_subscription(days: int = 3):
    return await _run_segment(
        "segment:newly_subscribed_users",
        """
        SELECT user_id
        FROM subscriptions
        WHERE status IN ('ACTIVE', 'TRIAL', 'FREE')
          AND started_at >= NOW() - (:days || ' days')::interval
        """,
        {"days": days},
    )


# ---------------------------------------------------------
# ACTIVE SUBSCRIBERS NOT USING FEATURES
# ---------------------------------------------------------
async def fetch_users_with_active_subscription_but_not_using_features():
    return await _run_segment(
        "segment:active_but_not_using_features",
        f"""
        SELECT s.user_id
        FROM subscriptions s
        JOIN usage_counters u ON u.subscription_id = s.id
        WHERE s.status IN {LIVE_STATUSES}
          AND u.period_end > NOW()
          AND (u.api_calls_used = 0 OR u.storage_used = 0)
        """,
    )


# ---------------------------------------------------------
# LOW-USAGE USERS (used < 50% of their plan limit)
# ---------------------------------------------------------
async def fetch_low_usage_users():
    return await _run_segment(
        "segment:low_usage_users",
        f"""
        SELECT s.user_id
        FROM subscriptions s
        JOIN usage_counters u ON u.subscription_id = s.id
        JOIN subscription_limits l ON l.subscription_id = s.id
        WHERE s.status IN {LIVE_STATUSES}
          AND l.api_calls_limit > 0
          AND (u.api_calls_used::float / l.api_calls_limit) < 0.5
        """,
    )


# ---------------------------------------------------------
# USERS WITH ZERO ACTIVITY
# ---------------------------------------------------------
async def fetch_users_with_zero_activity():
    return await _run_segment(
        "segment:users_with_zero_activity",
        f"""
        SELECT DISTINCT s.user_id
        FROM subscriptions s
        LEFT JOIN usage_counters u ON s.id = u.subscription_id
        WHERE s.status IN {LIVE_STATUSES}
          AND COALESCE(u.api_calls_used, 0) = 0
        """,
    )


# ---------------------------------------------------------
# USERS WITH INCOMPLETE ONBOARDING
# ---------------------------------------------------------
async def fetch_users_with_incomplete_onboarding():
    return await _run_segment(
        "segment:users_with_incomplete_onboarding",
        """
        SELECT id
        FROM users
        WHERE onboarding_completed = FALSE
        """,
    )


# ---------------------------------------------------------
# TRIAL ENDING SOON (within the next N days)
# ---------------------------------------------------------
async def fetch_users_trial_ending_soon(days: int = 2):
    return await _run_segment(
        "segment:trial_ending_soon",
        """
        SELECT user_id
        FROM subscriptions
        WHERE status = 'TRIAL'
          AND trial_ends_at IS NOT NULL
          AND trial_ends_at BETWEEN NOW() AND NOW() + (:days || ' days')::interval
        """,
        {"days": days},
    )


# ---------------------------------------------------------
# TRIAL EXPIRED BUT NOT CONVERTED
# ---------------------------------------------------------
async def fetch_users_trial_expired_but_not_converted():
    return await _run_segment(
        "segment:trial_expired_but_not_converted",
        """
        SELECT user_id
        FROM subscriptions
        WHERE status IN ('EXPIRED', 'CANCELLED')
          AND trial_ends_at IS NOT NULL
          AND billing_cycles_completed = 0
        """,
    )


# ---------------------------------------------------------
# USERS WHO NEVER STARTED A FREE TRIAL
# ---------------------------------------------------------
async def fetch_users_who_didnt_use_free():
    return await _run_segment(
        "segment:users_who_didnt_use_free",
        """
        SELECT u.id AS user_id
        FROM users u
        LEFT JOIN user_trials ut ON u.id = ut.user_id
        WHERE COALESCE(ut.used_free, FALSE) = FALSE
        """,
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(fetch_all_users())
