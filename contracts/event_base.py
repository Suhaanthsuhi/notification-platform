# contracts/event_base.py
"""
Event Base Contract Module

This module defines the core event contract for the notification platform.
It establishes the canonical structure that every incoming event must follow
before entering the enrichment pipeline.

Key Components:

1. EventTarget
   Defines the intended recipient of the event.
   Exactly one of the following must be specified:
   - user_id      → direct user notification
   - topic        → topic-based broadcast
   - broadcast    → global broadcast

   A model-level validator enforces mutual exclusivity to prevent
   ambiguous routing during the decision stage.

2. RawEvent
   Represents the validated structure of an incoming event.
   It includes:

   - Event identity (event_id, trace_id)
   - Event metadata (event_name, version, priority)
   - Source information (source_service, environment)
   - Timestamp (occurred_at)
   - Target definition (EventTarget)
   - Event-specific payload (data)

   Field-level validation ensures:
   - Priority is non-negative
   - Event name conforms to the EventType enum
   - Timestamp is parsed into a proper datetime object

Design Principles:

- Strong typing using Pydantic for runtime validation
- Strict contract enforcement before enrichment
- Clear separation between event metadata and event payload
- Deterministic routing based on target structure

Why This Matters:

This module forms the foundation of the event-driven architecture.
All downstream stages (enricher → engine → delivery) rely on this
validated structure to guarantee correctness and consistency.

Any malformed event is rejected at this layer, ensuring
the rest of the pipeline operates on trusted data.
"""

import re
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from contracts.event_types import EventType

# Event Target
class EventTarget(BaseModel):
    user_id: Optional[str] = None
    topic: Optional[str] = None
    broadcast: Optional[bool] = False

    @model_validator(mode="after")
    def validate_target(self):
        specified = [
            bool(self.user_id),
            bool(self.topic),
            bool(self.broadcast),
        ]

        if sum(specified) != 1:
            raise ValueError(
                "Exactly one of user_id, topic, or broadcast must be provided"
            )

        return self


# Raw Event (Base Contract)
class RawEvent(BaseModel):
    event_id: str
    trace_id: str

    event_name: EventType
    event_version: int

    source_service: str
    priority: int
    environment: str
    occurred_at: datetime

    target: EventTarget
    data: Dict[str, Any]

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value):
        if value < 0:
            raise ValueError("Priority must be >= 0")
        return value


# Common Validators
EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


__all__ = [
    "RawEvent",
    "EventTarget",
    "EMAIL_REGEX",
]