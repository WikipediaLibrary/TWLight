"""
Settings file intended for use in production, on WMF servers.  This file:

* overrides anything that needs server-specific values
* imports things that the base file draws from environment variables from a
  hardcoded file kept out of version control (unless their default value is
  correct in this context)
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

from .base import *
from .production_vars import (SECRET_KEY,
                              CONSUMER_KEY,
                              CONSUMER_SECRET,
                              MYSQL_PASSWORD)

ALLOWED_HOSTS = ['twlight-test.wmflabs.org',
                 'twl-test.wmflabs.org',
                 'wikipedialibrary.wmflabs.org']

DEBUG = False

# Can be replaced with option files:
# https://docs.djangoproject.com/en/1.7/ref/databases/#connecting-to-the-database
DATABASES['default']['USER'] = 'twlight'
DATABASES['default']['PASSWORD'] = MYSQL_PASSWORD

#EMAIL_BACKEND = 'djmail.backends.celery.EmailBackend'
DJMAIL_REAL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'Wikipedia Library Card Platform <noreply@twl-test.wmflabs.org>'
