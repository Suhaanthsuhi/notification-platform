# app/engine/templates/base.py
"""
Push Template Definitions Module

This module defines all push notification templates for the
notification decision engine.

Each template is registered using the @register_template decorator,
mapping an (event_name, channel) pair to a rendering function.
These functions transform an enriched event into a final
notification payload containing:

- title
- body
- meta (type, sub_type, language, deep link, etc.)

Core Responsibilities:
- Render user-facing notification content
- Apply language localization using TRANSLATIONS
- Resolve user language from enrichment context
- Construct dynamic deep links with optional query parameters
- Format template variables (e.g., plan name, usage count)

Template Structure:
Each template:
1. Extracts required data from enriched_event
2. Resolves language from user profile context
3. Retrieves translation content
4. Formats dynamic placeholders
5. Returns a structured payload ready for delivery

The `meta` object standardizes downstream processing by categorizing
notifications (WELCOME, SUBSCRIPTION, REPORT, USAGE_LIMIT, ENGAGEMENT, ...)
and embedding deep link URLs.

Design Principles:
- Separation of presentation logic from business logic
- Extensible template registration (no engine modification required)
- Channel-aware rendering (currently push, extensible to email/SMS)
- Localization-ready architecture

This module represents the presentation layer of the
event-driven notification pipeline.
"""

from typing import Dict
from urllib.parse import urlencode

from .registry import register_template
from .translations import TRANSLATIONS
from app.engine.deeplinks import scheme


def resolve_language(context: dict) -> str:
    profile = context.get("profile", {})
    return (
        profile.get("language")
        or context.get("language")
        or "en"
    )


def get_translation(event_name: str, language: str):
    event_translations = TRANSLATIONS.get(event_name, {})
    return event_translations.get(language) or event_translations.get("en")


def safe_format(text: str, **kwargs) -> str:
    """
    Format `text` with the provided kwargs, but never blow up if the string
    contains braces that aren't valid placeholders (common with manually
    authored campaign copy). Returns the original text on any format error.
    """
    if not text:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text


# ---------------------------------------------------------
# USER REGISTERED
# ---------------------------------------------------------

@register_template("USER_REGISTERED", "push")
def welcome_user_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})
    profile = context.get("profile", {})

    first_name = profile.get("firstname") or data.get("firstName") or "there"

    language = resolve_language(context)
    translation = get_translation("USER_REGISTERED", language)

    return {
        "title": safe_format(translation["title"], first_name=first_name),
        "body": translation["body"],
        "meta": {
            "type": "WELCOME",
            "language": language,
            "url": f"{scheme}://home",
        },
    }


# ---------------------------------------------------------
# SUBSCRIPTION PAGE ABANDONMENT (manual trigger)
# ---------------------------------------------------------

@register_template("SUBSCRIPTION_PAGE_ABANDONMENT", "push")
def subscription_page_abandonment_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})
    profile = context.get("profile", {})

    language = resolve_language(context)
    translation = get_translation("SUBSCRIPTION_PAGE_ABANDONMENT", language)

    first_name = profile.get("firstname") or "there"

    # Prefer the content supplied at trigger time; fall back to default copy.
    title = data.get("title") or translation["title"]
    body = data.get("body") or translation["body"]
    deeplink_url = data.get("url") or f"{scheme}://plans"

    return {
        "title": safe_format(title, first_name=first_name),
        "body": safe_format(body, first_name=first_name),
        "meta": {
            "type": "SUBSCRIPTION",
            "sub_type": "PAGE_ABANDONMENT",
            "language": language,
            "url": deeplink_url,
        },
    }


# ---------------------------------------------------------
# SUBSCRIPTION NOT STARTED
# ---------------------------------------------------------

@register_template("SUBSCRIPTION_NOT_STARTED", "push")
def subscription_not_started_v1(enriched_event: dict) -> Dict:
    context = enriched_event.get("context", {})
    language = resolve_language(context)
    translation = get_translation("SUBSCRIPTION_NOT_STARTED", language)

    return {
        "title": translation["title"],
        "body": translation["body"],
        "meta": {
            "type": "SUBSCRIPTION",
            "sub_type": "NOT_STARTED",
            "language": language,
            "url": f"{scheme}://plans",
        },
    }


# ---------------------------------------------------------
# SUBSCRIPTION TRIAL STARTED
# ---------------------------------------------------------

@register_template("SUBSCRIPTION_TRIAL_STARTED", "push")
def subscription_trial_started_v1(enriched_event: dict) -> Dict:
    context = enriched_event.get("context", {})
    language = resolve_language(context)
    translation = get_translation("SUBSCRIPTION_TRIAL_STARTED", language)

    return {
        "title": translation["title"],
        "body": translation["body"],
        "meta": {
            "type": "SUBSCRIPTION",
            "sub_type": "TRIAL_STARTED",
            "language": language,
            "url": f"{scheme}://billing",
        },
    }


# ---------------------------------------------------------
# SUBSCRIPTION ACTIVE
# ---------------------------------------------------------

@register_template("SUBSCRIPTION_ACTIVE", "push")
def subscription_active_v1(enriched_event: dict) -> Dict:
    context = enriched_event.get("context", {})
    language = resolve_language(context)
    translation = get_translation("SUBSCRIPTION_ACTIVE", language)

    return {
        "title": translation["title"],
        "body": translation["body"],
        "meta": {
            "type": "SUBSCRIPTION",
            "sub_type": "ACTIVE",
            "language": language,
            "url": f"{scheme}://billing",
        },
    }


# ---------------------------------------------------------
# SUBSCRIPTION CANCELLED
# ---------------------------------------------------------

@register_template("SUBSCRIPTION_CANCELLED", "push")
def subscription_cancelled_v1(enriched_event: dict) -> Dict:
    context = enriched_event.get("context", {})
    language = resolve_language(context)
    translation = get_translation("SUBSCRIPTION_CANCELLED", language)

    return {
        "title": translation["title"],
        "body": translation["body"],
        "meta": {
            "type": "SUBSCRIPTION",
            "sub_type": "CANCELLED",
            "language": language,
            "url": f"{scheme}://billing",
        },
    }


# ---------------------------------------------------------
# SUBSCRIPTION EXPIRED
# ---------------------------------------------------------

@register_template("SUBSCRIPTION_EXPIRED", "push")
def subscription_expired_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})

    plan = data.get("plan_name") or "your plan"
    language = resolve_language(context)
    translation = get_translation("SUBSCRIPTION_EXPIRED", language)

    return {
        "title": translation["title"],
        "body": safe_format(translation["body"], plan=plan),
        "meta": {
            "type": "SUBSCRIPTION",
            "sub_type": "EXPIRED",
            "language": language,
            "url": f"{scheme}://billing",
        },
    }


# ---------------------------------------------------------
# USAGE: API LIMIT REACHED
# ---------------------------------------------------------

@register_template("ALERT_API_USAGE_LIMIT_REACHED", "push")
def api_usage_limit_reached_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})

    usage = data.get("usage", 0)
    language = resolve_language(context)
    translation = get_translation("ALERT_API_USAGE_LIMIT_REACHED", language)

    return {
        "title": translation["title"],
        "body": safe_format(translation["body"], usage=usage),
        "meta": {
            "type": "USAGE_LIMIT",
            "sub_type": "API",
            "language": language,
            "url": f"{scheme}://billing",
        },
    }


# ---------------------------------------------------------
# USAGE: STORAGE LIMIT REACHED
# ---------------------------------------------------------

@register_template("ALERT_STORAGE_LIMIT_REACHED", "push")
def storage_limit_reached_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})

    usage = data.get("usage", 0)
    language = resolve_language(context)
    translation = get_translation("ALERT_STORAGE_LIMIT_REACHED", language)

    return {
        "title": translation["title"],
        "body": safe_format(translation["body"], usage=usage),
        "meta": {
            "type": "USAGE_LIMIT",
            "sub_type": "STORAGE",
            "language": language,
            "url": f"{scheme}://billing",
        },
    }


# ---------------------------------------------------------
# REPORTS: WEEKLY REPORT READY
# ---------------------------------------------------------

@register_template("WEEKLY_REPORT_READY", "push")
def weekly_report_ready_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})
    language = resolve_language(context)
    translation = get_translation("WEEKLY_REPORT_READY", language)

    report_id = data.get("report_id")
    params = {"reportId": report_id} if report_id else {}
    deeplink_url = (
        f"{scheme}://reports?{urlencode(params)}" if params else f"{scheme}://reports"
    )

    return {
        "title": translation["title"],
        "body": translation["body"],
        "meta": {
            "type": "REPORT",
            "sub_type": "WEEKLY",
            "language": language,
            "url": deeplink_url,
        },
    }


# ---------------------------------------------------------
# REPORTS: EXPORT READY
# ---------------------------------------------------------

@register_template("EXPORT_READY", "push")
def export_ready_v1(enriched_event: dict) -> Dict:
    data = enriched_event.get("data", {})
    context = enriched_event.get("context", {})
    language = resolve_language(context)
    translation = get_translation("EXPORT_READY", language)

    deeplink_url = data.get("download_url") or f"{scheme}://exports"

    return {
        "title": translation["title"],
        "body": translation["body"],
        "meta": {
            "type": "REPORT",
            "sub_type": "EXPORT",
            "language": language,
            "url": deeplink_url,
        },
    }


# =========================================================
# ENGAGEMENT TEMPLATES
# =========================================================

def _engagement_template(event_name: str, sub_type: str, path: str):
    """Factory for the simple engagement templates (no dynamic data)."""

    @register_template(event_name, "push")
    def _template(enriched_event: dict) -> Dict:
        context = enriched_event.get("context", {})
        language = resolve_language(context)
        translation = get_translation(event_name, language)

        return {
            "title": translation["title"],
            "body": translation["body"],
            "meta": {
                "type": "ENGAGEMENT",
                "sub_type": sub_type,
                "language": language,
                "url": f"{scheme}://{path}",
            },
        }

    _template.__name__ = f"{event_name.lower()}_v1"
    return _template


_engagement_template("ENG_FINISH_ONBOARDING", "ONBOARDING", "onboarding")
_engagement_template("ENG_COMPLETE_PROFILE", "PROFILE", "profile")
_engagement_template("ENG_FEATURE_ADOPTION", "FEATURE_ADOPTION", "features")
_engagement_template("ENG_INACTIVITY_NUDGE", "INACTIVITY", "home")
_engagement_template("ENG_WEEKLY_DIGEST", "DIGEST", "reports")
_engagement_template("ENG_NEW_FEATURE_ANNOUNCEMENT", "ANNOUNCEMENT", "features")
_engagement_template("ENG_USERS_LIKE_YOU", "SOCIAL_PROOF", "home")
_engagement_template("ENG_TRY_FREE_PLAN", "TRY_FREE_PLAN", "plans")
_engagement_template("ENG_TRIAL_ENDING_SOON", "TRIAL_ENDING", "billing")
_engagement_template("ENG_WINBACK", "WINBACK", "plans")
