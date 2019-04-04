"""
Settings file intended for use in local, on WMF servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/
from __future__ import print_function
import sys

from .local import *

# Migrations slow tests down considerably. Don't load them for tests.
MIGRATION_MODULES = {
    'admin': None,
    'applications': None,
    'auth': None,
    'contenttypes': None,
    'core': None,
    'django_comments': None,
    'default': None,
    'djmail': None,
    'requests': None,
    'resources': None,
    'reversion': None,
    'sessions': None,
    'sites': None,
    'taggit': None,
    'users': None,
}
