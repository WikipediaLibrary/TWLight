import os

# We're going to replace Django's default logging config.
import logging.config

# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
# We're replacing the default logging config to get better control of the
# mail_admins behavior.
# Logging is in another file since Django 3.1 because of https://code.djangoproject.com/ticket/32016

ADMINS = [("TWLight Developers", "librarycard-dev@lists.wikimedia.org")]
DJANGO_EMAIL_ADMINS_BACKEND = os.environ.get(
    "DJANGO_EMAIL_ADMINS_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
LOGGING_CONFIG = None

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
            "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
        },
        "formatters": {
            "django.server": {
                "()": "django.utils.log.ServerFormatter",
                "format": "[%(server_time)s] %(message)s",
            }
        },
        "handlers": {
            "nodebug_console": {
                "level": "WARNING",
                "filters": ["require_debug_false"],
                "class": "logging.StreamHandler",
            },
            "debug_console": {
                "level": "INFO",
                "filters": ["require_debug_true"],
                "class": "logging.StreamHandler",
            },
            "django.server": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "django.server",
            },
            "mail_admins": {
                "level": "ERROR",
                "filters": ["require_debug_false"],
                "class": "django.utils.log.AdminEmailHandler",
                "email_backend": DJANGO_EMAIL_ADMINS_BACKEND,
            },
        },
        "loggers": {
            "django": {
                "handlers": ["nodebug_console", "debug_console", "mail_admins"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            },
            "django.server": {
                "handlers": ["django.server"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
                "propagate": False,
            },
            "TWLight": {
                "handlers": ["nodebug_console", "debug_console", "mail_admins"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            },
        },
    }
)
