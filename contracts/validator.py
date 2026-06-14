# contracts/validator.py
"""
Contract Validation Module

Validates the integrity of the notification event contract
at application startup.

Checks performed:
1. Every EventType has a registered schema
2. Every EventType has a registered template
3. Every EventType has translations defined

If any contract piece is missing, the application will fail fast.
"""

from contracts.event_types import EventType
from contracts.event_registry import EVENT_SCHEMA_REGISTRY
from app.engine.templates.registry import TEMPLATE_REGISTRY
from app.engine.templates.translations import TRANSLATIONS


def validate_event_contracts():

    missing_schema = []
    missing_templates = []
    missing_translations = []

    for event in EventType:

        # Schema validation
        if event not in EVENT_SCHEMA_REGISTRY:
            missing_schema.append(event.value)

        # Template validation
        template_key = (event.value, "push")
        if template_key not in TEMPLATE_REGISTRY:
            missing_templates.append(event.value)

        # Translation validation
        if event.value not in TRANSLATIONS:
            missing_translations.append(event.value)

    errors = []

    if missing_schema:
        errors.append(
            f"Missing schemas for events: {missing_schema}"
        )

    if missing_templates:
        errors.append(
            f"Missing templates for events: {missing_templates}"
        )

    if missing_translations:
        errors.append(
            f"Missing translations for events: {missing_translations}"
        )

    if errors:
        raise RuntimeError(
            "Event contract validation failed:\n" + "\n".join(errors)
        )

    print("Event contracts validated successfully.")