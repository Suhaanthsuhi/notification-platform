# contracts/event_registry.py
"""
Event Schema Registry Module

This module maintains a registry that maps each EventType
to its corresponding Pydantic data schema.

Purpose:
The registry enables strict validation of event payloads
at runtime by linking event names to strongly typed models.
It ensures that every event’s `data` field conforms to
a predefined structure before entering the enrichment stage.

How It Works:
- EVENT_SCHEMA_REGISTRY stores:
    { EventType → Pydantic BaseModel }
- The @register_event_model decorator registers a schema
  class against a specific EventType.
- During validation, the system looks up the schema using
  the event name and validates `raw_event.data`.

Why This Is Important:
- Prevents malformed event payloads from propagating
- Enforces contract consistency across services
- Enables clear separation between event metadata
  and event-specific data structure
- Makes the system easily extensible

Extensibility Pattern:
To add a new event:
1. Define a new EventType
2. Create a Pydantic schema for its data
3. Register it using @register_event_model(EventType.X)

This registry forms the validation backbone of the
notification platform’s event-driven architecture.
"""

from typing import Dict, Type
from pydantic import BaseModel
from contracts.event_types import EventType

EVENT_SCHEMA_REGISTRY: Dict[EventType, Type[BaseModel]] = {}

def register_event_model(event_name: EventType):
    def decorator(cls: Type[BaseModel]):
        EVENT_SCHEMA_REGISTRY[event_name] = cls
        return cls
    return decorator