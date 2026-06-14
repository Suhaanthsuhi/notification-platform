# app/engine/templates/registry.py
"""
Template Registry Module

This module manages the registration and resolution of notification
templates used by the decision engine.

Templates are registered using a decorator-based approach and are
mapped by a composite key: (event_name, channel). This enables
channel-specific rendering logic for the same event.

Core Responsibilities:
- Register template functions for specific (event, channel) pairs
- Resolve the appropriate template at runtime
- Provide a fallback mechanism (defaulting to 'push' channel)
- Render the final notification payload from an enriched event

How It Works:
- Developers define a template function
- Decorate it with @register_template(event_name, channel)
- The function is stored in TEMPLATE_REGISTRY
- At runtime, render_template() retrieves and executes the correct template

If no template is found:
- resolve_template() attempts fallback to (event_name, 'push')
- If still not found, render_template() returns None

This design enables:
- Extensible template management
- Channel-specific customization (push, email, sms, etc.)
- Clean separation between event logic and presentation logic
- Pluggable template architecture without modifying core engine code
"""

from typing import Callable, Dict, Tuple, Optional

TemplateKey = Tuple[str, str]  # (event_name, channel)

TEMPLATE_REGISTRY: Dict[TemplateKey, Callable] = {}


def register_template(event_name: str, channel: str):
    def decorator(func: Callable):
        TEMPLATE_REGISTRY[(event_name, channel)] = func
        return func
    return decorator

def resolve_template(event_name: str, channel: str):
    key = (event_name, channel)

    if key in TEMPLATE_REGISTRY:
        return TEMPLATE_REGISTRY[key]

    return TEMPLATE_REGISTRY.get((event_name, 'push'))

def render_template(
    event_name: str,
    channel: str,
    enriched_event: dict
) -> Optional[Dict]:

    template_func = resolve_template(event_name, channel)

    if not template_func:
        return None

    return template_func(enriched_event)

__all__ = [
    'TEMPLATE_REGISTRY',
    'register_template',
    'resolve_template',
    'render_template',
]