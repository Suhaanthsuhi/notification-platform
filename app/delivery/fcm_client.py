# app/delivery/fcm_client.py
"""
FCM Client Module

This module provides an abstraction layer for sending push notifications
through Firebase Cloud Messaging (FCM). It encapsulates all interactions
with the firebase_admin SDK and standardizes how notifications are sent
to individual devices, multiple devices, or topics.

Core Responsibilities:
- Initialize Firebase Admin using service account credentials
- Send push notifications to a single device token
- Send multicast notifications to multiple device tokens
- Send topic-based notifications
- Normalize payload data to ensure APNS compatibility
- Handle and return structured error responses

Key Features:
- Asynchronous execution using asyncio.to_thread to avoid blocking
- Safe conversion of data payload values to strings (required by APNS)
- iOS-specific APNS configuration (priority, sound, badge, etc.)
- Structured success and failure reporting for delivery tracking

Design Principles:
- Channel abstraction (engine does not directly depend on Firebase)
- Cross-platform compatibility (Android via FCM, iOS via APNS through FCM)
- Minimal logic in delivery layer (business logic handled upstream)
- Clear separation between message construction and delivery result handling

This module represents the final outbound communication layer
of the notification pipeline.
"""

import json
import asyncio
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError
from typing import List, Dict, Any

from core import get_settings

settings = get_settings()


class FCMClient:

    def __init__(self):
        try:
            self._app = firebase_admin.get_app()
        except ValueError:
            raw = settings.firebase_service_account_json
            if raw and raw.startswith(("'", '"')) and raw.endswith(("'", '"')):
                raw = raw[1:-1]
            cred_dict = json.loads(raw)
            cred = credentials.Certificate(cred_dict)
            self._app = firebase_admin.initialize_app(cred)

    # --------------------------------------------------
    # Send to Single Token
    # --------------------------------------------------
    async def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:

        safe_data = {k: str(v) for k, v in (data or {}).items()}
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
            data=safe_data,
            apns=messaging.APNSConfig(
                headers={
                    "apns-priority": "10",
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        sound="default",
                        badge=1,
                    )
                ),
            ),
        )

        try:
            message_id = await asyncio.to_thread(
                messaging.send,
                message,
                False,
                self._app,
            )

            return {
                "success": True,
                "message_id": message_id,
            }

        except FirebaseError as e:
            return {
                "success": False,
                "error": str(e),
                "code": getattr(e, "code", None),
            }

    # --------------------------------------------------
    # Send to Multiple Tokens (Batch)
    # --------------------------------------------------
    async def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens,
            data=data or {},
            apns=messaging.APNSConfig(
                headers={
                    "apns-priority": "10",
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        sound="default",
                        badge=1,
                        content_available=True,
                        mutable_content=True,
                    )
                ),
            ),
        )

        try:
            response = await asyncio.to_thread(
                messaging.send_each_for_multicast,
                message,
                False,
                self._app,
            )

            failed_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    failed_tokens.append(tokens[idx])

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens,
            }

        except FirebaseError as e:
            return {
                "success": False,
                "error": str(e),
            }

    # --------------------------------------------------
    # Send to Topic
    # --------------------------------------------------
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic=topic,
            data=data or {},
        )

        try:
            message_id = await asyncio.to_thread(
                messaging.send,
                message,
                False,
                self._app,
            )

            return {
                "success": True,
                "message_id": message_id,
            }

        except FirebaseError as e:
            return {
                "success": False,
                "error": str(e),
            }