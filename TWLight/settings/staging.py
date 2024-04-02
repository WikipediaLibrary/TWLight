"""
Settings file intended for use on WMF staging servers.  This file:

* overrides anything that needs environment-specific values
"""

# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

from .server import *

# Needed to be added for /admin
CSRF_TRUSTED_ORIGINS = ["https://twlight-staging.wmflabs.org"]

DEFAULT_FROM_EMAIL = "Wikipedia Library Card Staging <staging@twl.wmflabs.org>"
