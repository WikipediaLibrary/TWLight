"""
Settings file intended for use in staging, on WMF servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

import sys
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

# Let Django know that allowed hosts are trusted for CSRF.
# Needed to be added for /admin
CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/var/tmp/django_cache",
    }
}

# GLITCHTIP CONFIGURATION
# ------------------------------------------------------------------------------
sentry_sdk.init(
    dsn="https://50e927aaca194181afe5c4b8e790d004@glitchtip-wikipedialibrary.wmflabs.org/1",
    integrations=[DjangoIntegration()],
)
