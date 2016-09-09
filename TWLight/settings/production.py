"""
Settings file intended for use in production, on WMF servers.  This file:

* overrides anything that needs server-specific values
* hardcodes things that the base file draws from environment variables (unless
  their default value is correct in this context)
"""

# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

import os

from .base import *

ALLOWED_HOSTS = ['twlight-test.wmflabs.org']

DEBUG = False
SECRET_KEY = '8s8=)1direp%&imkq@91l)*9ot9^v*x+p@_6asq4z$k9kn&k*8'

# Can be replaced with option files:
# https://docs.djangoproject.com/en/1.7/ref/databases/#connecting-to-the-database
DATABASES['default']['USER'] = 'TWLight'
DATABASES['default']['PASSWORD'] = os.environ.get('DJANGO_MYSQL_PASSWORD', '')

EMAIL_BACKEND = 'djmail.backends.celery.EmailBackend'
DJMAIL_REAL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
