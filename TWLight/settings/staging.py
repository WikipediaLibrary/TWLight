"""
Settings file intended for use in staging, on WMF servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/
from __future__ import print_function
import sys

from .base import *

# Let Django know that allowed hosts are trusted for CSRF.
# Needed to be added for /admin
CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

SERVER_EMAIL = "Wikipedia Library Card Staging <noreply@twlight-staging.wmflabs.org>"
DEFAULT_FROM_EMAIL = SERVER_EMAIL

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/var/tmp/django_cache",
    }
}
