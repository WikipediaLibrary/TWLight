"""
Settings file intended for use on WMF servers.  This file:

* overrides anything that needs values common to all servers
"""

# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

import sys
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from TWLight.settings.helpers import sentry_before_send

from .base import *

# Let Django know that allowed hosts are trusted for CSRF.
# Needed to be added for /admin
CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS
# Allow CSRF token access in JavaScript
CSRF_COOKIE_HTTPONLY = False

# Never debug on servers
DEBUG = False

# SecurityMiddleware configuration as suggested by
# python manage.py check --deploy
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

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
    before_send=sentry_before_send,
    environment=TWLIGHT_ENV,
)
