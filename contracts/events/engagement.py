# contracts/events/engagement.py
"""
Engagement / Lifecycle-Marketing Event Schemas

These events are emitted by the engagement scheduler (campaign engine)
rather than by upstream product services. They re-engage users based on
segment membership (onboarding incomplete, low usage, trial not started,
churned, etc.).

The content for each is fully resolved from templates + translations at
the engine stage, so the `data` payloads are intentionally empty.
"""

from contracts.event_types import EventType
from contracts.event_registry import register_event_model
from pydantic import BaseModel


@register_event_model(EventType.ENG_FINISH_ONBOARDING)
class EngFinishOnboardingData(BaseModel):
    pass


@register_event_model(EventType.ENG_COMPLETE_PROFILE)
class EngCompleteProfileData(BaseModel):
    pass


@register_event_model(EventType.ENG_FEATURE_ADOPTION)
class EngFeatureAdoptionData(BaseModel):
    pass


@register_event_model(EventType.ENG_INACTIVITY_NUDGE)
class EngInactivityNudgeData(BaseModel):
    pass


@register_event_model(EventType.ENG_WEEKLY_DIGEST)
class EngWeeklyDigestData(BaseModel):
    pass


@register_event_model(EventType.ENG_NEW_FEATURE_ANNOUNCEMENT)
class EngNewFeatureAnnouncementData(BaseModel):
    pass


@register_event_model(EventType.ENG_USERS_LIKE_YOU)
class EngUsersLikeYouData(BaseModel):
    pass


@register_event_model(EventType.ENG_TRY_FREE_PLAN)
class EngTryFreePlanData(BaseModel):
    pass


@register_event_model(EventType.ENG_TRIAL_ENDING_SOON)
class EngTrialEndingSoonData(BaseModel):
    pass


@register_event_model(EventType.ENG_WINBACK)
class EngWinbackData(BaseModel):
    pass
