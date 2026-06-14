# app/engagement/campaigns/definitions.py
"""
Campaign Definitions

Each campaign maps an engagement event to a user segment and a cooldown
window. The scheduler runs every campaign on a fixed cadence; for each
campaign it resolves the segment, then emits one event per eligible user
into the raw stream (subject to per-campaign cooldown and the daily cap).

Adding a campaign requires no engine/worker changes — just declare a class,
decorate it with @register_campaign, and point `segment()` at a registered
segment.
"""

from app.engagement.campaigns.base import BaseCampaign
from app.engagement.campaigns.registry import register_campaign
from app.engagement.segments.registry import SEGMENTS


def _segment(name: str):
    """Resolve and query a registered segment by name."""
    return SEGMENTS[name]().get_users()


@register_campaign
class SubscriptionReminderCampaign(BaseCampaign):
    name = "subscription_reminder"
    event_name = "SUBSCRIPTION_NOT_STARTED"
    cooldown_days = 3

    async def segment(self):
        return await _segment("users_without_subscription")


@register_campaign
class FinishOnboardingCampaign(BaseCampaign):
    name = "finish_onboarding"
    event_name = "ENG_FINISH_ONBOARDING"
    cooldown_days = 2

    async def segment(self):
        return await _segment("users_with_incomplete_onboarding")


@register_campaign
class CompleteProfileCampaign(BaseCampaign):
    name = "complete_profile"
    event_name = "ENG_COMPLETE_PROFILE"
    cooldown_days = 5

    async def segment(self):
        return await _segment("all_users")


@register_campaign
class FeatureAdoptionCampaign(BaseCampaign):
    name = "feature_adoption"
    event_name = "ENG_FEATURE_ADOPTION"
    cooldown_days = 3

    async def segment(self):
        return await _segment("active_but_not_using_features")


@register_campaign
class InactivityNudgeCampaign(BaseCampaign):
    name = "inactivity_nudge"
    event_name = "ENG_INACTIVITY_NUDGE"
    cooldown_days = 3

    async def segment(self):
        return await _segment("low_usage_users")


@register_campaign
class WeeklyDigestCampaign(BaseCampaign):
    name = "weekly_digest"
    event_name = "ENG_WEEKLY_DIGEST"
    cooldown_days = 7

    async def segment(self):
        return await _segment("all_users")


@register_campaign
class NewFeatureAnnouncementCampaign(BaseCampaign):
    name = "new_feature_announcement"
    event_name = "ENG_NEW_FEATURE_ANNOUNCEMENT"
    cooldown_days = 7

    async def segment(self):
        return await _segment("all_users")


@register_campaign
class UsersLikeYouCampaign(BaseCampaign):
    name = "users_like_you"
    event_name = "ENG_USERS_LIKE_YOU"
    cooldown_days = 7

    async def segment(self):
        return await _segment("all_users")


@register_campaign
class TrialEndingSoonCampaign(BaseCampaign):
    name = "trial_ending_soon"
    event_name = "ENG_TRIAL_ENDING_SOON"
    cooldown_days = 2

    async def segment(self):
        return await _segment("trial_ending_soon")


@register_campaign
class FreeTrialReminderCampaign(BaseCampaign):
    name = "free_trial_reminder"
    event_name = "ENG_TRY_FREE_PLAN"
    cooldown_days = 3

    async def segment(self):
        return await _segment("users_who_didnt_use_free")


@register_campaign
class WinbackCampaign(BaseCampaign):
    name = "winback"
    event_name = "ENG_WINBACK"
    cooldown_days = 4

    async def segment(self):
        return await _segment("trial_expired_but_not_converted")
