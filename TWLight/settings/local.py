"""
Settings file intended for use in local, on WMF servers.  This file:

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
    from .local_vars import (SECRET_KEY,
                                  TWLIGHT_OAUTH_PROVIDER_URL,
                                  TWLIGHT_OAUTH_CONSUMER_KEY,
                                  TWLIGHT_OAUTH_CONSUMER_SECRET,
                                  MYSQL_PASSWORD,
                                  ALLOWED_HOSTS,
                                  DEBUG,
                                  REQUEST_BASE_URL)
except ImportError:
    # If there's no local_vars file on this system (e.g. because it isn't
    # a local system), this import will fail, which can cause things
    # to fail (notably makemigrations).
    print('Cannot import from TWLight/settings/local_vars.py',
          'This is fine if you are not on a local system, as long as your '
          'settings file is something other than TWLight/settings/local, '
          'but it will cause the app to fail if you are trying to use '
          'local settings.',
          file=sys.stderr)
    raise

# Let Django know about external URLs in case they differ from internal
# Needed to be added for /admin
USE_X_FORWARDED_HOST = True

# Can be replaced with option files:
# https://docs.djangoproject.com/en/1.7/ref/databases/#connecting-to-the-database
DATABASES['default']['USER'] = 'twlight'
DATABASES['default']['PASSWORD'] = MYSQL_PASSWORD

DEFAULT_FROM_EMAIL = '<twlight.local@localhost.localdomain>'

# TEST CONFIGURATION
# ------------------------------------------------------------------------------

INSTALLED_APPS += [
    'django_nose',
]

# Use nose to run all tests
#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = [
    #'--with-coverage',
    '--cover-package=TWLight.applications,TWLight.emails,TWLight.graphs,TWLight.resources, TWLight.users',
    #'--nologcapture',
    #'--cover-html',
    #'--cover-html-dir=htmlcov',
]

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# Identical to base settings other than caching.

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'OPTIONS': {
            # Reiterating the default so we can add to it later.
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages'
            ),
            # We don't cache templates in local environments.
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        }
    },
]
