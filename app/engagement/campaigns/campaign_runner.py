# app/engagement/campaigns/campaign_runner.py
"""
Campaign Runner

Executes engagement campaigns by processing users in controlled batches.

Design:
- Users are processed in fixed-size batches (not all at once)
  to avoid memory pressure and event loop overload on large segments.
- A per-user daily campaign notification cap is enforced before
  emitting events, so we don't waste pipeline resources on
  notifications that would get throttled downstream anyway.
- Cooldown checks prevent duplicate campaign notifications.

Flow per user:
  1. Check cooldown  → skip if recently notified for this campaign
  2. Check daily cap → skip if user already received 3 campaign
                       notifications today
  3. Emit event      → publish to the raw stream
  4. Set cooldown    → prevent re-notification for cooldown_days
  5. Increment cap   → track daily campaign count for the user
"""

import asyncio
import logging

from core import RedisClient

from app.engagement.cooldown import (
    is_on_cooldown,
    set_cooldown,
)

from app.engagement.emitter import emit_event

# Max users processed concurrently within a batch
BATCH_SIZE = 50

# Max campaign notifications a single user can receive per day
MAX_DAILY_CAMPAIGN_NOTIFS = 3

# TTL for the daily cap counter (24 hours)
DAILY_CAP_WINDOW_SECONDS = 24 * 60 * 60

logger = logging.getLogger("ENGAGEMENT")

redis = RedisClient()


async def _check_daily_cap(user_id: str) -> bool:
    """
    Returns True if the user has already hit the daily campaign
    notification limit and should be skipped.
    """
    key = f"campaign:daily:{user_id}"

    count = await redis.increment_with_ttl(
        key=key,
        ttl_seconds=DAILY_CAP_WINDOW_SECONDS,
    )

    if count > MAX_DAILY_CAMPAIGN_NOTIFS:
        return True

    return False


async def process_user(user_id: str, campaign):
    """Process a single user for a campaign."""

    if await is_on_cooldown(user_id, campaign.event_name):
        return

    if await _check_daily_cap(user_id):
        logger.debug(
            "Daily campaign cap reached user_id=%s campaign=%s",
            user_id,
            campaign.name,
        )
        return

    await emit_event(campaign.event_name, user_id)

    await set_cooldown(
        user_id,
        campaign.event_name,
        campaign.cooldown_days,
    )


async def run_campaign(campaign):
    """
    Run a campaign in controlled batches.

    Instead of scheduling all users at once, processes them
    in chunks of BATCH_SIZE. Each batch runs concurrently
    via asyncio.gather, then the next batch starts.
    """

    users = await campaign.segment()

    total = len(users)
    logger.info(
        "Running campaign %s for %s users (batch_size=%s)",
        campaign.name,
        total,
        BATCH_SIZE,
    )

    processed = 0

    for i in range(0, total, BATCH_SIZE):
        batch = users[i : i + BATCH_SIZE]

        tasks = [process_user(user_id, campaign) for user_id in batch]
        await asyncio.gather(*tasks, return_exceptions=True)

        processed += len(batch)
        logger.debug(
            "Campaign %s progress: %s/%s",
            campaign.name,
            processed,
            total,
        )

    logger.info("Campaign %s completed (%s users processed)", campaign.name, total)
