"""
Settings file intended for use on WMF production servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

from .server import *

DEFAULT_FROM_EMAIL = (
    "Wikipedia Library Card Platform <noreply@wikipedialibrary.wmflabs.org>"
)
