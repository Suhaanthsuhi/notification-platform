# app/delivery/worker.py
"""
Delivery Worker Module

This module implements the final stage of the notification pipeline —
responsible for delivering push notifications to end users via FCM.

It consumes delivery tasks from the Redis DELIVERY_STREAM, resolves
recipient tokens, sends notifications through the FCMClient, and handles
success, failure, and token invalidation scenarios.

Core Responsibilities:
- Consume delivery tasks using Redis Streams (consumer groups)
- Resolve active device tokens for users
- Send push notifications (multicast, topic, broadcast)
- Handle delivery failures and push to DLQ
- Deactivate invalid or expired tokens
- Acknowledge processed stream messages
- Gracefully shutdown on system signals

Architecture Role:
This worker sits after:
    RAW → ENRICHER → ENGINE → DELIVERY

Where:
- Enricher validates + attaches context
- Engine applies business logic + renders template
- Delivery performs the actual push notification dispatch

Key Design Characteristics:
- At-least-once delivery semantics (Redis consumer groups)
- Fault isolation via DLQ stream
- Token lifecycle management (automatic deactivation)
- Structured logging for observability
- Clean separation between business logic (engine) and transport layer (delivery)

Failure Handling:
- Invalid payload → ACK and skip
- No active tokens → ACK and skip
- FCM failure → Send to DLQ
- Invalid tokens → Deactivate devices in DB
- Unexpected exception → DLQ + ACK

This module represents the outbound execution layer of the system,
where notification intent becomes real user-facing communication.
"""

import logging
import uuid
import json
import asyncio
import signal
from typing import List, Dict, Tuple

from core import RedisClient, get_settings
from app.delivery.fcm_client import FCMClient
from app.db.notification_repo import (
    get_tokens_from_user_id,
    deactivate_user_devices,
)

settings = get_settings()
logger = logging.getLogger("DELIVERY")

DELIVERY_STREAM = settings.redis_delivery_stream
DLQ_STREAM = settings.redis_dlq_stream

GROUP = "delivery_group"
CONSUMER = f"delivery-{uuid.uuid4()}"

stop_event = asyncio.Event()


# --------------------------------------------------
# Graceful Shutdown
# --------------------------------------------------
def handle_shutdown():
    logger.info("Shutdown signal received. Stopping delivery worker...")
    stop_event.set()


# --------------------------------------------------
# Fetch Active Tokens
# --------------------------------------------------
async def fetch_user_tokens(user_id: str) -> List[Dict]:
    logger.debug("Fetching tokens for user_id=%s", user_id)
    tokens = await get_tokens_from_user_id(user_id)
    logger.debug("Fetched %s tokens for user_id=%s", len(tokens), user_id)
    return tokens


# --------------------------------------------------
# Deactivate Invalid Tokens
# --------------------------------------------------
async def deactivate_tokens(devices: List[Dict]):
    if not devices:
        return

    device_pairs: List[Tuple[str, str]] = [
        (d["user_id"], d["device_id"])
        for d in devices
    ]

    logger.warning(
        "Deactivating %s invalid devices",
        len(device_pairs),
    )

    await deactivate_user_devices(device_pairs)


# --------------------------------------------------
# Worker
# --------------------------------------------------
async def delivery_worker():

    logger.info("Starting delivery worker consumer=%s", CONSUMER)

    r = RedisClient()
    fcm = FCMClient()

    await r.create_consumer_group(DELIVERY_STREAM, GROUP)
    logger.info("Consumer group ready stream=%s group=%s", DELIVERY_STREAM, GROUP)

    while not stop_event.is_set():

        try:
            messages = await r.xreadgroup(
                stream=DELIVERY_STREAM,
                group=GROUP,
                consumer=CONSUMER,
                count=10,
                block_ms=2000,
            )

            if messages:
                logger.debug("Fetched %s delivery messages", len(messages))

            for msg_id, fields in messages:

                try:
                    delivery_payload = json.loads(fields["payload"])

                    delivery_id = delivery_payload.get("delivery_id")
                    event_id = delivery_payload.get("event_id")
                    trace_id = delivery_payload.get("trace_id")

                    recipient_type = delivery_payload.get("recipient_type")
                    recipient = delivery_payload.get("recipient")

                    push_payload = delivery_payload.get("payload", {})
                    title = push_payload.get("title")
                    body = push_payload.get("body")
                    meta = push_payload.get("meta", {})

                    logger.info(
                        "Processing delivery_id=%s event_id=%s recipient_type=%s",
                        delivery_id,
                        event_id,
                        recipient_type,
                    )

                    # -----------------------------------
                    # Validate payload
                    # -----------------------------------
                    if not title or not body:
                        logger.error(
                            "Invalid payload structure delivery_id=%s",
                            delivery_id,
                        )
                        await r.xack(DELIVERY_STREAM, GROUP, msg_id)
                        logger.info("ACKed invalid payload message_id=%s", msg_id)
                        continue

                    # -----------------------------------
                    # USER DELIVERY
                    # -----------------------------------
                    if recipient_type == "user":

                        tokens_data = await fetch_user_tokens(recipient)

                        if not tokens_data:
                            logger.warning(
                                "No active tokens found user_id=%s delivery_id=%s",
                                recipient,
                                delivery_id,
                            )
                            await r.xack(DELIVERY_STREAM, GROUP, msg_id)
                            logger.info("ACKed no-token message_id=%s", msg_id)
                            continue

                        token_strings = [d["token"] for d in tokens_data]

                        logger.info(
                            "Sending multicast delivery_id=%s token_count=%s",
                            delivery_id,
                            len(token_strings),
                        )

                        result = await fcm.send_multicast(
                            tokens=token_strings,
                            title=title,
                            body=body,
                            data=meta,
                        )

                        logger.info(
                            "FCM result delivery_id=%s success=%s failure=%s",
                            delivery_id,
                            result.get("success_count"),
                            result.get("failure_count"),
                        )

                        # Handle invalid tokens
                        failed_tokens = result.get("failed_tokens", [])

                        if failed_tokens:
                            logger.warning(
                                "Invalid tokens detected delivery_id=%s count=%s",
                                delivery_id,
                                len(failed_tokens),
                            )

                            invalid_devices = [
                                d for d in tokens_data
                                if d["token"] in failed_tokens
                            ]

                            await deactivate_tokens(invalid_devices)

                    # -----------------------------------
                    # TOPIC DELIVERY
                    # -----------------------------------
                    elif recipient_type == "topic":

                        logger.info(
                            "Sending topic notification topic=%s delivery_id=%s",
                            recipient,
                            delivery_id,
                        )

                        result = await fcm.send_to_topic(
                            topic=recipient,
                            title=title,
                            body=body,
                            data=meta,
                        )

                        logger.info(
                            "Topic result delivery_id=%s success=%s",
                            delivery_id,
                            result.get("success"),
                        )

                        if not result.get("success"):
                            raise Exception(result.get("error"))

                    # -----------------------------------
                    # BROADCAST
                    # -----------------------------------
                    elif recipient_type == "broadcast":

                        logger.info(
                            "Sending broadcast notification delivery_id=%s",
                            delivery_id,
                        )

                        result = await fcm.send_to_topic(
                            topic="all",
                            title=title,
                            body=body,
                            data=meta,
                        )

                        logger.info(
                            "Broadcast result delivery_id=%s success=%s",
                            delivery_id,
                            result.get("success"),
                        )

                        if not result.get("success"):
                            raise Exception(result.get("error"))

                    else:
                        logger.error(
                            "Unknown recipient type delivery_id=%s type=%s",
                            delivery_id,
                            recipient_type,
                        )

                    # -----------------------------------
                    # ACK on success
                    # -----------------------------------
                    await r.xack(DELIVERY_STREAM, GROUP, msg_id)
                    logger.info("ACKed delivery message_id=%s", msg_id)

                except Exception as e:

                    logger.error(
                        "Delivery processing error message_id=%s error=%s",
                        msg_id,
                        str(e),
                    )

                    # Send to DLQ
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

                    await r.xack(DELIVERY_STREAM, GROUP, msg_id)
                    logger.info("ACKed failed delivery message_id=%s", msg_id)

        except Exception as e:
            logger.error("Worker loop error: %s", str(e))

    logger.info("Delivery worker stopped gracefully.")


# --------------------------------------------------
# Entry
# --------------------------------------------------
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown())
    signal.signal(signal.SIGINT, lambda s, f: handle_shutdown())

    asyncio.run(delivery_worker())