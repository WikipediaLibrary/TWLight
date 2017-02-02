"""
Settings file for staging  - imports from production.py because it should be
the same except where it absolutely must differ.
"""
from .production import *

ALLOWED_HOSTS = ['twlight-staging.wmflabs.org']
REQUEST_BASE_URL = 'https://twlight-staging.wmflabs.org'
