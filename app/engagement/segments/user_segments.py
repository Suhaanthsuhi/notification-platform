"""
User Segments

A segment is a named query that returns the list of user IDs it applies to.
Campaigns reference segments by name via the SEGMENTS registry, so adding a
new audience is a matter of writing one query and registering one class.
"""

from app.engagement.segments.base import BaseSegment
from app.engagement.segments.registry import register_segment

from app.db.subscription_repo import (
    fetch_all_users,
    fetch_users_without_subscription,
    fetch_users_with_active_subscription,
    fetch_users_with_new_subscription,
    fetch_users_with_active_subscription_but_not_using_features,
    fetch_low_usage_users,
    fetch_users_with_zero_activity,
    fetch_users_with_incomplete_onboarding,
    fetch_users_trial_ending_soon,
    fetch_users_trial_expired_but_not_converted,
    fetch_users_who_didnt_use_free,
)


# ---------------------------------------------------------
# BROAD
# ---------------------------------------------------------

@register_segment("all_users")
class AllUsersSegment(BaseSegment):
    async def get_users(self):
        return await fetch_all_users()


# ---------------------------------------------------------
# PRE-SUBSCRIPTION
# ---------------------------------------------------------

@register_segment("users_without_subscription")
class UsersWithoutSubscriptionSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_without_subscription()


@register_segment("users_who_didnt_use_free")
class UsersWhoDidntUseFreeSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_who_didnt_use_free()


@register_segment("trial_ending_soon")
class TrialEndingSoonSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_trial_ending_soon()


@register_segment("trial_expired_but_not_converted")
class TrialExpiredButNotConvertedSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_trial_expired_but_not_converted()


# ---------------------------------------------------------
# ACTIVE SUBSCRIPTION
# ---------------------------------------------------------

@register_segment("users_with_active_subscription")
class UsersWithActiveSubscriptionSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_with_active_subscription()


@register_segment("newly_subscribed_users")
class NewlySubscribedUsersSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_with_new_subscription()


@register_segment("active_but_not_using_features")
class ActiveButNotUsingFeaturesSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_with_active_subscription_but_not_using_features()


# ---------------------------------------------------------
# ENGAGEMENT / USAGE
# ---------------------------------------------------------

@register_segment("users_with_incomplete_onboarding")
class UsersWithIncompleteOnboardingSegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_with_incomplete_onboarding()


@register_segment("low_usage_users")
class LowUsageUsersSegment(BaseSegment):
    async def get_users(self):
        return await fetch_low_usage_users()


@register_segment("users_with_zero_activity")
class UsersWithZeroActivitySegment(BaseSegment):
    async def get_users(self):
        return await fetch_users_with_zero_activity()
