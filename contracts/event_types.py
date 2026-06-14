# contracts/event_types.py
"""
EventType Enumeration Module

This module defines all supported notification event types
within the notification platform.

The EventType enum acts as the central contract for the entire
event-driven pipeline. Every event flowing through the system
(Raw -> Enriched -> Decision -> Delivery) must belong to one of
these predefined types.

Why This Matters:
- Prevents invalid or unknown events from entering the system
- Enables strict validation in the enricher stage
- Drives template resolution in the engine
- Ensures consistent naming across services
- Acts as a shared contract between producer services and the
  notification platform

Categories Covered:
1. User lifecycle events
2. Subscription lifecycle events
3. Usage limit alerts
4. Async job / report events
5. Engagement / lifecycle-marketing events

Design Characteristics:
- Inherits from `str` for JSON serialization compatibility
- Used as a key in:
    - EVENT_SCHEMA_REGISTRY
    - TEMPLATE_REGISTRY
    - TRANSLATIONS
- Enforces type safety across the system

Any new notification type must be:
1. Added here
2. Registered in the event schema registry
3. Provided with a template
4. Provided with translations (if required)

This enum is the authoritative source of truth for all supported
notification events. The catalog below is a generic SaaS example set;
swap it for your own product's events.
"""

from enum import Enum


class EventType(str, Enum):
    # ---- User lifecycle ----
    USER_REGISTERED = "USER_REGISTERED"

    # ---- Subscription lifecycle ----
    SUBSCRIPTION_NOT_STARTED = "SUBSCRIPTION_NOT_STARTED"
    SUBSCRIPTION_TRIAL_STARTED = "SUBSCRIPTION_TRIAL_STARTED"
    SUBSCRIPTION_ACTIVE = "SUBSCRIPTION_ACTIVE"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"

    # Manually-triggered campaign (content supplied at trigger time)
    SUBSCRIPTION_PAGE_ABANDONMENT = "SUBSCRIPTION_PAGE_ABANDONMENT"

    # ---- Usage / quota alerts ----
    ALERT_API_USAGE_LIMIT_REACHED = "ALERT_API_USAGE_LIMIT_REACHED"
    ALERT_STORAGE_LIMIT_REACHED = "ALERT_STORAGE_LIMIT_REACHED"

    # ---- Async jobs / reports ----
    WEEKLY_REPORT_READY = "WEEKLY_REPORT_READY"
    EXPORT_READY = "EXPORT_READY"

    # ---- Engagement / lifecycle marketing ----
    ENG_FINISH_ONBOARDING = "ENG_FINISH_ONBOARDING"
    ENG_COMPLETE_PROFILE = "ENG_COMPLETE_PROFILE"
    ENG_FEATURE_ADOPTION = "ENG_FEATURE_ADOPTION"
    ENG_INACTIVITY_NUDGE = "ENG_INACTIVITY_NUDGE"
    ENG_WEEKLY_DIGEST = "ENG_WEEKLY_DIGEST"
    ENG_NEW_FEATURE_ANNOUNCEMENT = "ENG_NEW_FEATURE_ANNOUNCEMENT"
    ENG_USERS_LIKE_YOU = "ENG_USERS_LIKE_YOU"
    ENG_TRY_FREE_PLAN = "ENG_TRY_FREE_PLAN"
    ENG_TRIAL_ENDING_SOON = "ENG_TRIAL_ENDING_SOON"
    ENG_WINBACK = "ENG_WINBACK"


__all__ = [
    "EventType",
]
