"""
Base settings for TWLight project.

This is not intended to be used as the live settings file for a project and will
not work as one. You should instead use production.py, local.py, or another file
that you write. These files should live in the settings directory; start with
'from .base import *'; and proceed to add or override settings as appropriate to
their context. In particular, you will need to set ALLOWED_HOSTS before your app
will run.

If you want to use production settings, you are now done.  If not, you will also
need to set the environment variables indicated in the README.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------------------
# ------------------------> core django configurations <------------------------
# ------------------------------------------------------------------------------

# APP CONFIGURATION
# ------------------------------------------------------------------------------

DJANGO_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

THIRD_PARTY_APPS = ()

TWLIGHT_APPS = (
    'TWLight.users',
    'TWLight.resources',
    'TWLight.applications',
)

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + TWLIGHT_APPS



# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


# DEBUG
# ------------------------------------------------------------------------------

# By setting this an an environment variable, it is easy to switch debug on in
# servers to do a quick test.
# DEBUG SHOULD BE FALSE ON PRODUCTION for security reasons.
DEBUG = bool(os.environ.get('DJANGO_DEBUG', True))


# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

# WMF sysadmins strongly prefer mysql, so use that.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twlight',
        'USER': os.environ.get('DJANGO_DB_USER', None),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', None),
        'HOST': 'localhost',
        'PORT': '3306',
    }
}


# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# In production, this list should contain the URL of the server and nothing
# else, for security reasons. For local testing '*' is OK.
ALLOWED_HOSTS = []

ROOT_URLCONF = 'TWLight.urls'

WSGI_APPLICATION = 'TWLight.wsgi.application'


# INTERNATIONALIZATION CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)


# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'


# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'brief': {
            'format': '%(asctime)s %(levelname)s %(name)s[%(funcName)s]: %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'twlight.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter': 'brief',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
        }
    }
}


# ------------------------------------------------------------------------------
# -----------------> third-party and TWLight configurations <-------------------
# ------------------------------------------------------------------------------


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)
