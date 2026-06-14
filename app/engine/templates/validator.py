from contracts.event_types import EventType
from app.engine.templates.registry import TEMPLATE_REGISTRY


def validate_all_templates():

    missing = []

    for event in EventType:

        key = (event.value, "push")

        if key not in TEMPLATE_REGISTRY:
            missing.append(event.value)

    if missing:
        raise RuntimeError(
            f"Missing templates for events: {missing}"
        )

    print("All event templates validated successfully")