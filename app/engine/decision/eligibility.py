# app/engine/decision/eligibility.py
"""
Eligibility Module

This module defines the decision logic for determining whether
an enriched event should result in a notification.

It evaluates user preferences present in the enrichment context
and returns a boolean indicating whether delivery should proceed.

Currently, eligibility is based solely on the user's
`notification_opt_in` preference.
"""

# Should we send notification?
def should_send_notification(enriched_event: dict) -> bool:
    context = enriched_event.get("context", {})
    preferences = context.get("preferences", {})

    if not preferences.get("notification_opt_in", False):
        return False

    return True