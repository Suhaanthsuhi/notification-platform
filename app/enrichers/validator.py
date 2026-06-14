# app/enrichers/validator.py
"""
Validator Module

This module is responsible for validating incoming raw events
before they enter the enrichment stage of the notification pipeline.

The validate_event function performs two levels of validation:

1. Base Event Validation
   The incoming dictionary is first validated against the
   RawEvent contract to ensure required top-level fields
   (event_id, trace_id, event_name, target, etc.) are present
   and correctly structured.

2. Event-Specific Data Validation
   Based on the event_name, the corresponding schema is
   retrieved from EVENT_SCHEMA_REGISTRY. The event's `data`
   payload is then validated against its registered Pydantic model.

If an event_name is not registered, a ValueError is raised.
If the event data does not match its schema, validation fails
immediately and the event is rejected.

This ensures:
- Strong schema enforcement at the boundary
- Contract-driven event architecture
- Protection against malformed or unsupported events
- Early failure before enrichment or delivery

The function returns a validated RawEvent object that is
safe to process in downstream stages.
"""

from contracts.event_base import RawEvent
from contracts.event_registry import EVENT_SCHEMA_REGISTRY

def validate_event(raw_event: dict) -> RawEvent:
    event = RawEvent(**raw_event)

    try:
        schema = EVENT_SCHEMA_REGISTRY[event.event_name]
    except KeyError:
        raise ValueError(f"Unsupported Event: {event.event_name.value}")

    # validate raw_event.data with Registered BaseModel in EVENT_SCHEMA_REGISTRY
    schema(**event.data)
    return event