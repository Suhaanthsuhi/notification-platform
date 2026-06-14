# app/engine/deeplinks.py
"""
Deep Link Scheme

Templates build client-side deep link URLs (e.g. `notifty://billing`) that
the mobile/web app intercepts to route the user to the right screen when a
notification is tapped. Change `scheme` to match your app's URL scheme.
"""

import os

scheme = os.getenv("DEEPLINK_SCHEME", "notifty")
