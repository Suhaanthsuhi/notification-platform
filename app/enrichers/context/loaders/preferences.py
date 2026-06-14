# app/enrichers/context/loaders/preferences.py
"""
Preference Context Loader Module.

This module defines a concrete implementation of the BaseContextLoader
responsible for attaching user notification preference data during the
event enrichment stage.

The loader checks whether the incoming event targets a specific user.
If so, it injects preference-related metadata into the enrichment context.
"""

from app.enrichers.context.registry import register_loader
from app.enrichers.context.base import BaseContextLoader

@register_loader
class PreferenceContextLoader(BaseContextLoader):

    async def load(self, event):
        if not event.target.user_id:
            return {}

        return {
            "preferences": {
                "notification_opt_in": True,
                "categories": ["default"]
            }
        }

__all__ = ["PreferenceContextLoader"]