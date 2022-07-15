"""
Settings file intended for use in local, on WMF servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

import sys

from .base import *

DEFAULT_FROM_EMAIL = "<twlight.local@localhost.localdomain>"

# TEST CONFIGURATION
# ------------------------------------------------------------------------------
# Using a less secure, but faster, password hasher for testing
if "test" in sys.argv:
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
    # Stop whitenoise from inspecting static files when testing
    WHITENOISE_AUTOREFRESH = True
    TEST_RUNNER = "TWLight.runner.TimeLoggingTestRunner"

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# Identical to base settings other than caching.

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "OPTIONS": {
            # Reiterating the default so we can add to it later.
            "context_processors": (
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ),
            # We don't cache templates in local environments.
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    }
]

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
# Identical to base settings other than making Whitenoise happy in dev and test.

WHITENOISE_AUTOREFRESH = True
STATICFILES_STORAGE = "whitenoise.storage.StaticFilesStorage"
