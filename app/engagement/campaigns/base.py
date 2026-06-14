# app/engagement/campaigns/base.py
"""
Base Campaign Definition
"""

from abc import ABC, abstractmethod


class BaseCampaign(ABC):

    name: str
    event_name: str
    cooldown_days: int

    @abstractmethod
    async def segment(self):
        """
        Return list of user_ids
        """
        raise NotImplementedError