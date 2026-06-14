# app/enrichers/context/loaders/profile.py
"""
Profile Context Loader Module.

This module defines a concrete implementation of the BaseContextLoader
responsible for attaching user profile data during the event
enrichment stage.

The loader checks whether the incoming event targets a specific user.
If so, it injects profile-related metadata into the enrichment context.
"""

from app.enrichers.context.base import BaseContextLoader
from app.enrichers.context.registry import register_loader
from app.db.profile_repo import get_user_by_user_id

@register_loader
class ProfileContextLoader(BaseContextLoader):

    async def load(self, event):
        user_id = event.target.user_id

        if not user_id:
            return {}

        user = await get_user_by_user_id(user_id)

        if not user:
            return {}

        return {
            'profile': user
        }

__all__ = ["ProfileContextLoader"]