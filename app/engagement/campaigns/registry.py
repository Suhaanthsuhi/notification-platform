# app/engagement/campaigns/registry.py
"""
Campaign Registry
"""

from typing import List, Type
from .base import BaseCampaign

CAMPAIGNS: List[Type[BaseCampaign]] = []


def register_campaign(cls: Type[BaseCampaign]):
    CAMPAIGNS.append(cls)
    return cls