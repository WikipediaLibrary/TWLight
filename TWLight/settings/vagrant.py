"""
Settings file intended for use in vagrant, on WMF servers.  This file:

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
    from .vagrant_vars import (SECRET_KEY,
                                  WP_CREDENTIALS,
                                  MYSQL_PASSWORD,
                                  ALLOWED_HOSTS,
                                  DEBUG,
                                  REQUEST_BASE_URL)
except ImportError:
    # If there's no vagrant_vars file on this system (e.g. because it isn't
    # a vagrant system), this import will fail, which can cause things
    # to fail (notably makemigrations).
    print('Cannot import from TWLight/settings/vagrant_vars.py',
          'This is fine if you are not on a vagrant system, as long as your '
          'settings file is something other than TWLight/settings/vagrant, '
          'but it will cause the app to fail if you are trying to use '
          'vagrant settings.',
          file=sys.stderr)
    raise

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
DEFAULT_FROM_EMAIL = 'Wikipedia Library Card Platform <noreply@twl-test.wmflabs.org>'
