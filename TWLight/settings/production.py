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

DJANGO_DEBUG = False
SECRET_KEY = '8s8=)1direp%&imkq@91l)*9ot9^v*x+p@_6asq4z$k9kn&k*8'

# Can be replaced with option files:
# https://docs.djangoproject.com/en/1.7/ref/databases/#connecting-to-the-database
DATABASES['default'] = {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twlight',
        'USER': 'twlight',
        'PASSWORD': 'Rf6@(y]@"&7;Dv]G',
        'HOST': 'localhost',
        'PORT': '3306',
}
