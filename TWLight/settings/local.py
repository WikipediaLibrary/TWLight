import os
from .base import *

# This is a totally insecure setting that should never be used in production,
# but it simplifies things for local development.
ALLOWED_HOSTS = ['*']

# DJMAIL CONFIGURATION
# ------------------------------------------------------------------------------

# Allows for sending actual email, for testing purposes.
DJMAIL_REAL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_PASSWORD')
EMAIL_PORT = 587
EMAIL_SENDING_OKAY = True

# TEST CONFIGURATION
# ------------------------------------------------------------------------------

INSTALLED_APPS += (
    'django_nose',
)

# Use nose to run all tests
#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = [
    #'--with-coverage',
    '--cover-package=TWLight.applications,TWLight.emails,TWLight.graphs,TWLight.resources, TWLight.users',
    #'--nologcapture',
    #'--cover-html',
    #'--cover-html-dir=htmlcov',
]
