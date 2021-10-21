"""
Settings file intended for use on WMF staging servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

from .server import *

DEFAULT_FROM_EMAIL = (
    "Wikipedia Library Card Staging <noreply@twlight-staging.wmflabs.org>"
)
