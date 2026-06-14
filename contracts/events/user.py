from contracts.event_types import EventType
from contracts.event_registry import register_event_model
from pydantic import BaseModel
from typing import Literal, Optional


@register_event_model(EventType.USER_REGISTERED)
class UserRegisteredData(BaseModel):
    platform: Literal["android", "ios", "web"]
    app_version: Optional[str] = None
