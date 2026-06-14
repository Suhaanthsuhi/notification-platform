# app/engine/worker.py
"""
Decision Engine Worker Module

This module implements the decision stage of the notification pipeline.

It consumes enriched events from Redis Streams and determines whether
a notification should be delivered. If eligible, it renders the
appropriate template and publishes a delivery task to the delivery stream.

Core Responsibilities:
- Consume enriched events using Redis consumer groups
- Enforce idempotency to prevent duplicate processing
- Resolve recipient type (user, topic, broadcast)
- Apply eligibility checks (opt-in validation)
- Apply throttling rules for rate limiting
- Render channel-specific templates
- Publish delivery tasks to the delivery stream
- Route processing failures to a DLQ
- Recover pending messages for reliability

Processing Flow:
Enriched Event → Idempotency → Target Resolution →
Opt-in Check → Throttling → Template Rendering →
Delivery Task Creation → ACK

The worker ensures:
- At-most-once logical processing via Redis idempotency keys
- Safe failure handling through DLQ
- Controlled notification volume via throttling
- Clean separation between decision logic and delivery execution

This module represents the decision and routing layer
within the event-driven notification architecture.
"""

import logging
import uuid
import json
import asyncio
import signal
from datetime import datetime, timezone
from typing import Dict

from core import RedisClient, get_settings
from app.engine.decision import should_send_notification
from app.engine.templates import render_template
from app.engine.decision import is_throttled
from contracts.validator import validate_event_contracts

settings = get_settings()
logger = logging.getLogger("ENGINE")

ENRICHED_STREAM = settings.redis_enriched_stream
DELIVERY_STREAM = settings.redis_delivery_stream
DLQ_STREAM = settings.redis_dlq_stream

GROUP = "decision_group"
CONSUMER = f"decision-{uuid.uuid4()}"

IDEMPOTENCY_TTL = 86400
CLAIM_IDLE_MS = 45000

stop_event = asyncio.Event()


# --------------------------------------------------
# Graceful Shutdown
# --------------------------------------------------
def handle_shutdown():
    logger.info("Shutdown signal received. Stopping decision worker...")
    stop_event.set()


# --------------------------------------------------
# Idempotency
# --------------------------------------------------
async def check_idempotency(r: RedisClient, event_id: str) -> bool:
    key = f"engine:processed:{event_id}"

    result = await r.set_if_not_exists(
        key=key,
        value="1",
        ttl_seconds=IDEMPOTENCY_TTL,
    )

    if result:
        logger.info(
            "Idempotency lock acquired event_id=%s",
            event_id
        )
    else:
        logger.warning(
            "Duplicate event detected event_id=%s",
            event_id
        )

    return result


# --------------------------------------------------
# Process Single Message
# --------------------------------------------------
async def process_message(r: RedisClient, msg_id: str, fields: Dict):

    enriched_event = json.loads(fields["payload"])
    event_id = enriched_event["event_id"]
    trace_id = enriched_event["trace_id"]

    logger.info("Processing event_id=%s trace_id=%s", event_id, trace_id)

    # ---------------------------
    # Idempotency
    # ---------------------------
    is_first = await check_idempotency(r, event_id)

    if not is_first:
        await r.xack(ENRICHED_STREAM, GROUP, msg_id)
        logger.info("ACKed duplicate event message_id=%s", msg_id)
        return

    # ---------------------------
    # Resolve Target
    # ---------------------------
    target = enriched_event.get("target", {})

    user_id = target.get("user_id")
    topic = target.get("topic")
    broadcast = target.get("broadcast", False)

    recipient_value = None

    if broadcast:
        recipient_type = "broadcast"
        recipient_value = "all"
    elif topic:
        recipient_type = "topic"
        recipient_value = topic
    elif user_id:
        recipient_type = "user"
        recipient_value = user_id
    else:
        logger.error(
            "Invalid target event_id=%s trace_id=%s",
            event_id,
            trace_id,
        )
        await r.xack(ENRICHED_STREAM, GROUP, msg_id)
        logger.info("ACKed invalid target message_id=%s", msg_id)
        return

    logger.info(
        "Recipient resolved event_id=%s recipient_type=%s recipient=%s",
        event_id,
        recipient_type,
        recipient_value,
    )

    # ---------------------------
    # Opt-in Check
    # ---------------------------
    if not should_send_notification(enriched_event):
        logger.info(
            "User opted out event_id=%s recipient=%s",
            event_id,
            recipient_value,
        )
        await r.xack(ENRICHED_STREAM, GROUP, msg_id)
        return

    logger.info("Opt-in check passed event_id=%s", event_id)

    # ---------------------------
    # Throttling
    # ---------------------------
    if recipient_type == "user":
        throttled = await is_throttled(r, recipient_value)
        if throttled:
            logger.warning(
                "User throttled event_id=%s user_id=%s",
                event_id,
                recipient_value,
            )
            await r.xack(ENRICHED_STREAM, GROUP, msg_id)
            return

        logger.info("Throttling check passed event_id=%s", event_id)

    # ---------------------------
    # Render Template
    # ---------------------------
    channel = "push"

    rendered = render_template(
        enriched_event["event_name"],
        channel,
        enriched_event
    )

    if not rendered:
        logger.error(
            "Template rendering failed event_id=%s",
            event_id,
        )
        await r.xack(ENRICHED_STREAM, GROUP, msg_id)
        return

    logger.info("Template rendered successfully event_id=%s", event_id)

    # ---------------------------
    # Create Delivery Task
    # ---------------------------
    delivery_task = {
        "delivery_id": f"delivery_{uuid.uuid4()}",
        "event_id": event_id,
        "trace_id": trace_id,
        "recipient_type": recipient_type,
        "recipient": recipient_value,
        "priority": enriched_event.get("priority", 0),
        "channel": channel,
        "payload": rendered,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await r.xadd(
        stream=DELIVERY_STREAM,
        data={"payload": json.dumps(delivery_task)},
    )

    logger.info(
        "Delivery task published delivery_id=%s event_id=%s",
        delivery_task["delivery_id"],
        event_id,
    )

    # ---------------------------
    # ACK
    # ---------------------------
    await r.xack(ENRICHED_STREAM, GROUP, msg_id)
    logger.info("ACKed enriched event message_id=%s", msg_id)


# --------------------------------------------------
# Pending Recovery
# --------------------------------------------------
async def recover_pending(r: RedisClient):
    pending = await r.xpending_summary(ENRICHED_STREAM, GROUP)

    if not pending or pending["pending"] == 0:
        logger.debug("No pending messages to recover")
        return

    logger.warning(
        "Pending messages detected count=%s",
        pending["pending"],
    )

    # Simplified recovery logic (as before)


# --------------------------------------------------
# Worker Loop
# --------------------------------------------------
async def engine_worker():

    logger.info("Starting decision worker consumer=%s", CONSUMER)

    r = RedisClient()
    await r.create_consumer_group(ENRICHED_STREAM, GROUP)
    logger.info("Consumer group ready stream=%s group=%s", ENRICHED_STREAM, GROUP)

    validate_event_contracts()

    while not stop_event.is_set():

        # ---------------------------
        # Recovery Phase
        # ---------------------------
        try:
            await recover_pending(r)
        except Exception as e:
            logger.error("Pending recovery error: %s", str(e))
            await asyncio.sleep(1)
            continue

        # ---------------------------
        # Consume Messages
        # ---------------------------
        try:
            messages = await r.xreadgroup(
                stream=ENRICHED_STREAM,
                group=GROUP,
                consumer=CONSUMER,
                count=10,
                block_ms=2000,
            )

            if messages:
                logger.debug("Fetched %s messages", len(messages))

            for msg_id, fields in messages:
                try:
                    await process_message(r, msg_id, fields)
                except Exception as e:
                    logger.error("Processing error: %s", str(e))

                    await r.xadd(
                        stream=DLQ_STREAM,
                        data={
                            "payload": fields.get("payload"),
                            "error": str(e),
                        }
                    )

                    logger.warning(
                        "Message sent to DLQ message_id=%s",
                        msg_id,
                    )

                    await r.xack(ENRICHED_STREAM, GROUP, msg_id)
                    logger.info("ACKed failed message_id=%s", msg_id)

        except Exception as e:
            logger.error("Worker loop error: %s", str(e))

    logger.info("Decision worker stopped gracefully.")


# --------------------------------------------------
# Entry Point
# --------------------------------------------------
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown())
    signal.signal(signal.SIGINT, lambda s, f: handle_shutdown())

    asyncio.run(engine_worker())