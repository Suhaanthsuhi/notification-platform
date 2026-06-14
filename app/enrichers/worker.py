# app/enrichers/worker.py
"""
Enricher Worker Module

This module implements the enrichment stage of the notification pipeline.

It consumes raw events from a Redis Stream using a consumer group,
validates them against registered schemas, applies idempotency protection,
loads additional contextual data (profile, preferences, etc.), and publishes
the enriched event to the next stream.

Core Responsibilities:
- Consume raw events reliably using Redis Streams
- Validate event structure and data contracts
- Enforce idempotency using Redis SETNX with TTL
- Load contextual data via registered context loaders
- Publish enriched events to the enriched stream
- Route invalid events to a DLQ (Dead Letter Queue)
- Recover and reclaim stuck pending messages

The worker is fault-tolerant:
- Validation failures go to DLQ
- Duplicate events are safely ignored
- Idle pending messages are automatically reclaimed
- Processing is acknowledged only after successful enrichment

This ensures reliable, exactly-once-like processing semantics
within an event-driven notification architecture.
"""

import logging
import uuid
import json
import asyncio
import signal
from datetime import datetime, timezone

from core import get_settings, RedisClient
from app.enrichers.validator import validate_event
from app.enrichers.context_loader import load_context
from contracts.validator import validate_event_contracts

settings = get_settings()
logger = logging.getLogger("ENRICHER")

RAW_STREAM = settings.redis_raw_stream
ENRICHED_STREAM = settings.redis_enriched_stream
DLQ_STREAM = settings.redis_dlq_stream

GROUP = "enricher_group"
CONSUMER = f"enricher-{uuid.uuid4()}"

IDEMPOTENCY_TTL = 86400
CLAIM_IDLE_MS = 45000
RECOVERY_INTERVAL = 30

stop_event = asyncio.Event()


def handle_shutdown():
    logger.info("Shutdown signal received. Stopping enricher worker...")
    stop_event.set()


async def process_message(r: RedisClient, msg_id: str, fields: dict):

    raw_event = json.loads(fields["payload"])
    trace_id = raw_event.get("trace_id")
    event_id = raw_event.get("event_id")

    logger.info("Processing message_id=%s trace_id=%s", msg_id, trace_id)

    # ---------------------------
    # Validation
    # ---------------------------
    try:
        event = validate_event(raw_event)
        logger.info("Validation successful event_id=%s", event.event_id)

    except Exception as e:
        logger.error(
            "Validation failed event_id=%s trace_id=%s error=%s",
            event_id,
            trace_id,
            str(e),
        )

        await r.xadd(
            stream=DLQ_STREAM,
            data={
                "payload": json.dumps(raw_event),
                "error": str(e),
            }
        )

        logger.info("Event sent to DLQ event_id=%s", event_id)

        await r.xack(RAW_STREAM, GROUP, msg_id)
        logger.info("Raw message ACKed after validation failure message_id=%s", msg_id)
        return

    # ---------------------------
    # Idempotency
    # ---------------------------
    idempotency_key = f"notif:processed:{event.event_id}"

    is_first = await r.set_if_not_exists(
        key=idempotency_key,
        value="1",
        ttl_seconds=IDEMPOTENCY_TTL,
    )

    if not is_first:
        logger.warning(
            "Duplicate event detected event_id=%s trace_id=%s",
            event.event_id,
            trace_id,
        )
        await r.xack(RAW_STREAM, GROUP, msg_id)
        logger.info("Raw message ACKed duplicate message_id=%s", msg_id)
        return

    logger.info("Idempotency lock acquired event_id=%s", event.event_id)

    # ---------------------------
    # Load Context
    # ---------------------------
    try:
        context = await load_context(event)
        logger.info("Context loaded successfully event_id=%s", event.event_id)
    except Exception as e:
        logger.error(
            "Context loading failed event_id=%s error=%s",
            event.event_id,
            str(e),
        )

        await r.xadd(
            stream=DLQ_STREAM,
            data={
                "payload": json.dumps(raw_event),
                "error": f"Context loading failed: {str(e)}",
            }
        )

        await r.xack(RAW_STREAM, GROUP, msg_id)
        logger.info("Raw message ACKed after context failure message_id=%s", msg_id)
        return

    enriched_event = {
        **raw_event,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "context": context,
    }

    # ---------------------------
    # Publish Enriched Event
    # ---------------------------
    try:
        await r.xadd(
            stream=ENRICHED_STREAM,
            data={"payload": json.dumps(enriched_event)},
        )

        logger.info(
            "Enriched event published successfully event_id=%s",
            event.event_id,
        )

    except Exception as e:
        logger.error(
            "Failed to publish enriched event event_id=%s error=%s",
            event.event_id,
            str(e),
        )
        return

    # ---------------------------
    # ACK Raw Event
    # ---------------------------
    await r.xack(RAW_STREAM, GROUP, msg_id)
    logger.info("Raw event ACKed successfully message_id=%s", msg_id)


async def recover_pending_messages(r: RedisClient):
    try:
        summary = await r.xpending_summary(RAW_STREAM, GROUP)

        if summary and summary["pending"] > 0:
            logger.info("Pending messages detected count=%s", summary["pending"])

            pending = await r.get_client().xpending_range(
                RAW_STREAM,
                GROUP,
                min="-",
                max="+",
                count=10,
            )

            message_ids = [
                entry["message_id"]
                for entry in pending
                if entry["time_since_delivered"] > CLAIM_IDLE_MS
            ]

            if message_ids:
                logger.info("Reclaiming idle messages ids=%s", message_ids)

                claimed = await r.xclaim(
                    stream=RAW_STREAM,
                    group=GROUP,
                    consumer=CONSUMER,
                    min_idle_ms=CLAIM_IDLE_MS,
                    message_ids=message_ids,
                )

                logger.info("Claimed %s messages for recovery", len(claimed))

                for msg_id, fields in claimed:
                    await process_message(r, msg_id, fields)
            else:
                logger.debug("No idle messages eligible for reclaim")

    except Exception as e:
        logger.error("Pending recovery error: %s", str(e))


async def enricher_worker():

    logger.info("Starting enricher worker consumer=%s", CONSUMER)

    r = RedisClient()
    await r.create_consumer_group(RAW_STREAM, GROUP)
    logger.info("Consumer group ready stream=%s group=%s", RAW_STREAM, GROUP)

    last_recovery_check = 0

    validate_event_contracts()

    while not stop_event.is_set():

        try:
            messages = await r.xreadgroup(
                stream=RAW_STREAM,
                group=GROUP,
                consumer=CONSUMER,
                count=10,
                block_ms=2000,
            )

            if messages:
                logger.debug("Fetched %s messages from stream", len(messages))

            for msg_id, fields in messages:
                await process_message(r, msg_id, fields)

            now = asyncio.get_event_loop().time()
            if now - last_recovery_check > RECOVERY_INTERVAL:
                logger.debug("Running periodic pending recovery")
                await recover_pending_messages(r)
                last_recovery_check = now

        except Exception as e:
            logger.error("Worker loop error: %s", str(e))

    logger.info("Enricher worker stopped gracefully.")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown())
    signal.signal(signal.SIGINT, lambda s, f: handle_shutdown())

    asyncio.run(enricher_worker())