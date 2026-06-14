# contracts/events/usage.py
"""
Usage / Quota Alert Event Schemas

Schemas for events fired when a user approaches or reaches a plan limit
(API calls, storage, seats, etc.). These typically drive an upsell or
add-on purchase.
"""

from contracts.event_types import EventType
from contracts.event_registry import register_event_model
from pydantic import BaseModel
from typing import Optional


@register_event_model(EventType.ALERT_API_USAGE_LIMIT_REACHED)
class ApiUsageLimitReachedData(BaseModel):
    subscription_id: str
    usage: int
    plan_name: Optional[str] = None


@register_event_model(EventType.ALERT_STORAGE_LIMIT_REACHED)
class StorageLimitReachedData(BaseModel):
    subscription_id: str
    usage: int
    plan_name: Optional[str] = None
