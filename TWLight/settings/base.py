"""
Base settings for TWLight project.

This is not intended to be used as the live settings file for a project
and will not work as one. You should instead use production.py, local.py,
or another file that you write. These files should live in the settings
directory; start with 'from .base import *'; and proceed to add or
override settings as appropriate to their context. In particular, you
will need to set ALLOWED_HOSTS before your app will run. You will also
need to set the environment variables indicated in the README.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
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
    'django.middleware.security.SecurityMiddleware',
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

# TWLight _REQUIRES POSTGRES_ because the Editor model uses a postgres-specific
# field type. Do not substitute mysql or other databases.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'twlight',
        # No user/pass here for ease of local development.
        # production.py adds a user and a password to this setting.
        'HOST': 'localhost',
        'PORT': '5432',
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


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

# DJANGO-ALLAUTH
# ------------------------------------------------------------------------------

# See https://django-allauth.readthedocs.org/en/latest/installation.html

# Allauth requires 'django.template.context_processors.request' to be in
# TEMPLATES[0]OPTIONS['context_processors']; it is by default, above.

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

ALLAUTH_NEEDED_APPS = (
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # Allauth supports lots of social account providers, but not Wikipedia.
    # Therefore we ignore all their built-in providers and supply our own.
    #'TWLight.wp_allauth'
)

INSTALLED_APPS += ALLAUTH_NEEDED_APPS

SITE_ID = 1

# Allauth also requires some URL configuration; see the top-level urls.py.