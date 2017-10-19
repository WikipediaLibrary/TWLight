"""
Settings file intended for use in production, on WMF servers.  This file:

* overrides anything that needs server-specific values
* imports things that the base file draws from environment variables from a
  hardcoded file kept out of version control (unless their default value is
  correct in this context)
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/
from __future__ import print_function
import sys

from .base import *
try:
    from .production_vars import (SECRET_KEY,
                                  TWLIGHT_OAUTH_PROVIDER_URL,
                                  TWLIGHT_OAUTH_CONSUMER_KEY,
                                  TWLIGHT_OAUTH_CONSUMER_SECRET,
                                  MYSQL_PASSWORD,
                                  ALLOWED_HOSTS,
                                  REQUEST_BASE_URL)
except ImportError:
    # If there's no production_vars file on this system (e.g. because it isn't
    # a production system), this import will fail, which can cause things
    # to fail (notably makemigrations).
    print('Cannot import from TWLight/settings/production_vars.py',
          'This is fine if you are not on a production system, as long as your '
          'settings file is something other than TWLight/settings/production, '
          'but it will cause the app to fail if you are trying to use '
          'production settings.',
          file=sys.stderr)
    raise

# Let Django know about external URLs in case they differ from internal
# Needed to be added for /admin
USE_X_FORWARDED_HOST = True

# Never debug in prod
DEBUG = False

# Can be replaced with option files:
# https://docs.djangoproject.com/en/1.7/ref/databases/#connecting-to-the-database
DATABASES['default']['USER'] = 'twlight'
DATABASES['default']['PASSWORD'] = MYSQL_PASSWORD

#EMAIL_BACKEND = 'djmail.backends.celery.EmailBackend'
DJMAIL_REAL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_BACKEND = 'djmail.backends.default.EmailBackend'
EMAIL_HOST = 'tools-mail.tools.eqiad.wmflabs'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False # Important, or you will get an SMTPException on wmlabs
DEFAULT_FROM_EMAIL = 'Wikipedia Library Card Platform <noreply@wikipedialibrary.wmflabs.org>'

# SecurityMiddleware configuration as suggested by
# python manage.py check --deploy
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
    }
}
