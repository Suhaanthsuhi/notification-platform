# contracts/events/subscription.py
"""
Subscription Event Schemas Module

This module defines Pydantic data schemas for subscription-related
events in the notification platform.

Each schema represents the structure of the `data` field for a specific
EventType and is registered using the @register_event_model decorator.

Purpose:
- Enforce strict validation of event-specific payloads
- Define clear contracts between producer services and the
  notification system
- Prevent malformed or incomplete subscription events from entering
  the pipeline

How It Works:
Each class:
1. Inherits from Pydantic BaseModel
2. Defines the required and optional fields for that event
3. Is automatically registered in EVENT_SCHEMA_REGISTRY via the decorator

During validation:
- The enricher stage resolves the schema using EventType
- The raw event's `data` field is validated against the corresponding model
- Any mismatch raises an exception and routes the event to DLQ

Design Characteristics:
- Optional fields allow flexible payload evolution
- Strong typing ensures reliable template rendering
- Clear separation between event metadata (RawEvent) and event-specific
  payload (these models)
"""

from datetime import datetime
from contracts.event_types import EventType
from contracts.event_registry import register_event_model
from pydantic import BaseModel
from typing import Optional


@register_event_model(EventType.SUBSCRIPTION_NOT_STARTED)
class SubscriptionNotStartedData(BaseModel):
    pass


@register_event_model(EventType.SUBSCRIPTION_PAGE_ABANDONMENT)
class SubscriptionPageAbandonmentData(BaseModel):
    # Manually-triggered campaign. The notification content is supplied at
    # trigger time and carried in the event `data`. All fields are optional;
    # the template falls back to default copy when a field is omitted.
    # `title` / `body` may contain a {first_name} placeholder, which is filled
    # from the enriched profile context.
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None


@register_event_model(EventType.SUBSCRIPTION_TRIAL_STARTED)
class SubscriptionTrialStartedData(BaseModel):
    subscription_id: str
    plan_name: Optional[str] = None
    trial_starts_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None


@register_event_model(EventType.SUBSCRIPTION_ACTIVE)
class SubscriptionActiveData(BaseModel):
    subscription_id: str
    plan_name: Optional[str] = None
    amount: Optional[str] = None


@register_event_model(EventType.SUBSCRIPTION_CANCELLED)
class SubscriptionCancelledData(BaseModel):
    subscription_id: str
    plan_name: Optional[str] = None
    amount: Optional[str] = None


@register_event_model(EventType.SUBSCRIPTION_EXPIRED)
class SubscriptionExpiredData(BaseModel):
    subscription_id: str
    plan_name: Optional[str] = None
    amount: Optional[str] = None
