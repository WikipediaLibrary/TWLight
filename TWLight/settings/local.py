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

SECRET_KEY = os.environ.get('SECRET_KEY', None)
TWLIGHT_OAUTH_PROVIDER_URL = os.environ.get('TWLIGHT_OAUTH_PROVIDER_URL', None)
TWLIGHT_OAUTH_CONSUMER_KEY = os.environ.get('TWLIGHT_OAUTH_CONSUMER_KEY', None)
TWLIGHT_OAUTH_CONSUMER_SECRET = os.environ.get('TWLIGHT_OAUTH_CONSUMER_SECRET', None)
MYSQL_USER = os.environ.get('MYSQL_USER', None)
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', None)
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', None).split(' ')
DEBUG = os.environ.get('DEBUG', False)
REQUEST_BASE_URL = os.environ.get('REQUEST_BASE_URL', None)

# Let Django know about external URLs in case they differ from internal
# Needed to be added for /admin
USE_X_FORWARDED_HOST = True

# Can be replaced with option files:
# https://docs.djangoproject.com/en/1.7/ref/databases/#connecting-to-the-database
DATABASES['default']['USER'] = MYSQL_USER
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
