# app/enrichers/context/registry.py
"""
Context Loader Registry Module.

This module provides a central registry for all context loader
implementations used during the enrichment stage of the
notification pipeline.

Context loaders are registered via the `@register_loader` decorator.
The enrichment engine dynamically iterates over all registered
loaders to assemble the complete context for an incoming event.

This design enables extensibility without modifying the core
enrichment logic (Open/Closed Principle).
"""

from typing import List, Type
from .base import BaseContextLoader

CONTEXT_LOADERS: List[Type[BaseContextLoader]] = []

def register_loader(loader: Type[BaseContextLoader]):
    CONTEXT_LOADERS.append(loader)
    return loader