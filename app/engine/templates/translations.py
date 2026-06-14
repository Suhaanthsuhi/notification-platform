# app/engine/templates/translations.py
"""
Translations Module

This module defines localized notification message templates used by the
template rendering engine.

It maps each event_name to a dictionary of language-specific translations.
Each translation contains a structured payload with:

- title
- body

The templates may include dynamic placeholders (e.g. {first_name}, {plan},
{usage}) which are formatted at render time using enriched event data.

Key Characteristics:
- Language fallback is handled by the template layer (defaults to "en")
- Structured per-event organization
- Easily extensible for new languages
- Keeps presentation content separate from logic

This is a demo catalog shipping English (en) and Spanish (es). Add more
languages by adding keys alongside "en" / "es".
"""

TRANSLATIONS = {

    # ---------------------------------------------------------
    # USER REGISTERED
    # ---------------------------------------------------------
    "USER_REGISTERED": {
        "en": {
            "title": "Welcome, {first_name} 🎉",
            "body": "Thanks for signing up! Take a quick tour to get started.",
        },
        "es": {
            "title": "Bienvenido, {first_name} 🎉",
            "body": "¡Gracias por registrarte! Haz un recorrido rápido para empezar.",
        },
    },

    # ---------------------------------------------------------
    # SUBSCRIPTION
    # ---------------------------------------------------------
    # Manual / triggered campaign. Content is normally supplied at trigger
    # time; this entry is the default fallback used when no content is passed.
    "SUBSCRIPTION_PAGE_ABANDONMENT": {
        "en": {
            "title": "Still thinking it over? 🤔",
            "body": "You're one step away from upgrading. Tap to finish checking out.",
        },
        "es": {
            "title": "¿Aún lo estás pensando? 🤔",
            "body": "Estás a un paso de mejorar tu plan. Toca para completar la compra.",
        },
    },

    "SUBSCRIPTION_NOT_STARTED": {
        "en": {
            "title": "Unlock premium features 🚀",
            "body": "Start a plan to access advanced features, higher limits, and priority support.",
        },
        "es": {
            "title": "Desbloquea funciones premium 🚀",
            "body": "Activa un plan para acceder a funciones avanzadas, límites más altos y soporte prioritario.",
        },
    },

    "SUBSCRIPTION_TRIAL_STARTED": {
        "en": {
            "title": "Your free trial has started 🎉",
            "body": "Enjoy full access to every premium feature during your trial. Make the most of it!",
        },
        "es": {
            "title": "Tu prueba gratuita ha comenzado 🎉",
            "body": "Disfruta de acceso completo a todas las funciones premium durante tu prueba. ¡Aprovéchalo!",
        },
    },

    "SUBSCRIPTION_ACTIVE": {
        "en": {
            "title": "Subscription activated ✅",
            "body": "Your plan is now active. Enjoy uninterrupted premium access.",
        },
        "es": {
            "title": "Suscripción activada ✅",
            "body": "Tu plan ya está activo. Disfruta de acceso premium sin interrupciones.",
        },
    },

    "SUBSCRIPTION_CANCELLED": {
        "en": {
            "title": "Subscription cancelled",
            "body": "Your subscription has been cancelled. You can resubscribe anytime to regain access.",
        },
        "es": {
            "title": "Suscripción cancelada",
            "body": "Tu suscripción ha sido cancelada. Puedes volver a suscribirte cuando quieras.",
        },
    },

    "SUBSCRIPTION_EXPIRED": {
        "en": {
            "title": "Subscription expired",
            "body": "Your {plan} has expired. Renew now to keep using premium features.",
        },
        "es": {
            "title": "Suscripción vencida",
            "body": "Tu {plan} ha vencido. Renueva ahora para seguir usando las funciones premium.",
        },
    },

    # ---------------------------------------------------------
    # USAGE LIMIT ALERTS
    # ---------------------------------------------------------
    "ALERT_API_USAGE_LIMIT_REACHED": {
        "en": {
            "title": "API limit reached ⚠️",
            "body": "You've used {usage} API calls on your plan. Upgrade or add an add-on to keep going.",
        },
        "es": {
            "title": "Límite de API alcanzado ⚠️",
            "body": "Has usado {usage} llamadas a la API de tu plan. Mejora tu plan o añade un complemento para continuar.",
        },
    },

    "ALERT_STORAGE_LIMIT_REACHED": {
        "en": {
            "title": "Storage almost full ⚠️",
            "body": "You've used {usage}% of your storage. Upgrade your plan to free up space.",
        },
        "es": {
            "title": "Almacenamiento casi lleno ⚠️",
            "body": "Has usado el {usage}% de tu almacenamiento. Mejora tu plan para liberar espacio.",
        },
    },

    # ---------------------------------------------------------
    # REPORTS / ASYNC JOBS
    # ---------------------------------------------------------
    "WEEKLY_REPORT_READY": {
        "en": {
            "title": "Your weekly report is ready 📊",
            "body": "This week's summary is in. Tap to see your latest insights.",
        },
        "es": {
            "title": "Tu informe semanal está listo 📊",
            "body": "Ya tienes el resumen de esta semana. Toca para ver tus últimas métricas.",
        },
    },

    "EXPORT_READY": {
        "en": {
            "title": "Your export is ready 📁",
            "body": "Your data export has finished. Tap to download it.",
        },
        "es": {
            "title": "Tu exportación está lista 📁",
            "body": "La exportación de tus datos ha terminado. Toca para descargarla.",
        },
    },

    # ---------------------------------------------------------
    # ENGAGEMENT
    # ---------------------------------------------------------
    "ENG_FINISH_ONBOARDING": {
        "en": {
            "title": "Finish setting up your account",
            "body": "You're almost there — complete setup in under 2 minutes.",
        },
        "es": {
            "title": "Termina de configurar tu cuenta",
            "body": "Ya casi terminas: completa la configuración en menos de 2 minutos.",
        },
    },

    "ENG_COMPLETE_PROFILE": {
        "en": {
            "title": "Complete your profile 👤",
            "body": "Add a few details to personalize your experience.",
        },
        "es": {
            "title": "Completa tu perfil 👤",
            "body": "Añade algunos datos para personalizar tu experiencia.",
        },
    },

    "ENG_FEATURE_ADOPTION": {
        "en": {
            "title": "Have you tried this yet? 💡",
            "body": "Discover a feature that can save you time today.",
        },
        "es": {
            "title": "¿Ya probaste esto? 💡",
            "body": "Descubre una función que puede ahorrarte tiempo hoy.",
        },
    },

    "ENG_INACTIVITY_NUDGE": {
        "en": {
            "title": "We miss you 👋",
            "body": "It's been a while. Jump back in and pick up where you left off.",
        },
        "es": {
            "title": "Te echamos de menos 👋",
            "body": "Ha pasado un tiempo. Vuelve y continúa donde lo dejaste.",
        },
    },

    "ENG_WEEKLY_DIGEST": {
        "en": {
            "title": "Your week at a glance 🗓",
            "body": "Here's what happened in your account this week.",
        },
        "es": {
            "title": "Tu semana de un vistazo 🗓",
            "body": "Esto es lo que pasó en tu cuenta esta semana.",
        },
    },

    "ENG_NEW_FEATURE_ANNOUNCEMENT": {
        "en": {
            "title": "✨ Something new just landed",
            "body": "We just shipped a new feature we think you'll love. Take a look.",
        },
        "es": {
            "title": "✨ Acaba de llegar algo nuevo",
            "body": "Acabamos de lanzar una función que creemos que te encantará. Échale un vistazo.",
        },
    },

    "ENG_USERS_LIKE_YOU": {
        "en": {
            "title": "👥 Teams like yours are loving this",
            "body": "Join thousands of users getting more done every day.",
        },
        "es": {
            "title": "👥 A equipos como el tuyo les encanta esto",
            "body": "Únete a miles de usuarios que logran más cada día.",
        },
    },

    "ENG_TRY_FREE_PLAN": {
        "en": {
            "title": "🎁 Try premium for free",
            "body": "Start your free trial today — no credit card required.",
        },
        "es": {
            "title": "🎁 Prueba premium gratis",
            "body": "Comienza tu prueba gratuita hoy, sin tarjeta de crédito.",
        },
    },

    "ENG_TRIAL_ENDING_SOON": {
        "en": {
            "title": "⏳ Your trial ends soon",
            "body": "Upgrade now to keep your premium features without interruption.",
        },
        "es": {
            "title": "⏳ Tu prueba termina pronto",
            "body": "Mejora tu plan ahora para conservar tus funciones premium sin interrupciones.",
        },
    },

    "ENG_WINBACK": {
        "en": {
            "title": "Come back and save 💜",
            "body": "We'd love to have you back. Here's a little something to welcome you.",
        },
        "es": {
            "title": "Vuelve y ahorra 💜",
            "body": "Nos encantaría tenerte de vuelta. Aquí tienes un detalle de bienvenida.",
        },
    },

}

__all__ = ["TRANSLATIONS"]
