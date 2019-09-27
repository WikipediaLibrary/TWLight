"""
Settings file intended for use in production, on WMF servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/
from __future__ import print_function
import sys

from .base import *

# Let Django know that allowed hosts are trusted for CSRF.
# Needed to be added for /admin
CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

# Never debug in prod
DEBUG = False

SERVER_EMAIL = 'Wikipedia Library Card Platform <noreply@wikipedialibrary.wmflabs.org>'
DEFAULT_FROM_EMAIL = SERVER_EMAIL

# SecurityMiddleware configuration as suggested by
# python manage.py check --deploy
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
    }
}
