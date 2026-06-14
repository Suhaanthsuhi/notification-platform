# app/enrichers/context/base.py
"""
Context Loader Base Module.

This module defines the abstract base class for all context loaders
used during the enrichment stage of the notification pipeline.

Context loaders are responsible for fetching additional domain-specific
data (e.g., user profile, preferences, metadata) and attaching it to
incoming events before delivery decision logic is applied.

All concrete loaders must implement the `load()` coroutine and return
a dictionary representing the enrichment context.
"""

from abc import ABC, abstractmethod

class BaseContextLoader(ABC):

    @abstractmethod
    async def load(self, event) -> dict:
        pass