# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

import os

from .base import *

# This is the settings file that should be used in production. Before it is
# ready for use, the following must be set:
# ALLOWED_HOSTS = ['url.of.production.server']

# See also the README.md for any environment configuration that needs to
# happen.

DATABASES['default']['USER'] = 'postgres'
DATABASES['default']['PASSWORD'] = os.environ.get('DJANGO_POSTGRES_PASSWORD')
