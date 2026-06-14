# app/engagement/engine.py
"""
Engagement Engine
Runs all campaigns
"""

from app.engagement.campaigns.registry import CAMPAIGNS
from app.engagement.campaigns.campaign_runner import run_campaign
import logging

logger = logging.getLogger("ENGAGEMENT")

async def run_all_campaigns():

    campaigns = [cls() for cls in CAMPAIGNS]

    logger.info("Registered campaigns: %s", CAMPAIGNS)

    for campaign in campaigns:

        await run_campaign(campaign)