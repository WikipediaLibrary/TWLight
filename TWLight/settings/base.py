"""
Base settings for TWLight project.

This is not intended to be used as the live settings file for a project and will
not work as one. You should instead use production.py, local.py, heroku.py, or
another file that you write. These files should live in the settings directory;
start with 'from .base import *'; and proceed to add or override settings as
appropriate to their context. In particular, you will need to set ALLOWED_HOSTS
before your app will run.

If you want to use production settings, you are now done.  If not, you will also
need to set the environment variables indicated in the README.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import os

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'media')

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
    'django.contrib.sites',         # required by django.contrib.comments
)

THIRD_PARTY_APPS = (
    'crispy_forms',
    'reversion',
    'autocomplete_light',
    'django_comments',
    'modeltranslation',
    'taggit',
    # DO NOT CONFUSE THIS with requests, the Python URL library! This is
    # django-request, the user analytics package.
    'request',
)

TWLIGHT_APPS = (
    'TWLight.i18n',
    'TWLight.users',
    'TWLight.resources',
    'TWLight.applications',
    'TWLight.emails',
    'TWLight.graphs',
)

# autocomplete_light and modeltranslation must go before django.contrib.admin.
INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + TWLIGHT_APPS


# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    # LocaleMiddleware must go after Session (and Cache, if used), but before
    # Common.
    'django.middleware.locale.LocaleMiddleware',
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

# WMF sysadmins strongly prefer mysql, so use that.
# If you're deploying to Heroku, heroku.py will override this.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twlight',
        'USER': os.environ.get('DJANGO_DB_USER', None),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', None),
        'HOST': 'localhost',
        'PORT': '3306',
        # This is critical for handling Unicode data due to stupid properties
        # of MySQL; see https://stackoverflow.com/questions/2108824/mysql-incorrect-string-value-error-when-save-unicode-string-in-django .
        'OPTIONS': {'charset': 'utf8mb4'},
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

SITE_ID = 1


# INTERNATIONALIZATION CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us' # Sets site default language.

# First tuple element should be a standard language code; see
# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes .
# Second is the human-readable form.
# In the language choice dropdown, languages will appear -in the order listed
# here-, regardless of how they ought to be alphabetized in the target
# language.
LANGUAGES = (
  #Transaltor: Text used for setting language to English
  ('en', _('English')),
  #Transaltor: Text used for setting language to Finnish
  ('fi', _('Finnish')),
  #Transaltor: Text used for setting language to French
  ('fr', _('French')),
)

LOCALE_PATHS = (
    # makemessages looks for locale/ in the top level, not the project level.
    os.path.join(os.path.dirname(BASE_DIR), 'locale'),
)

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
        'OPTIONS': {
            # Reiterating the default so we can add to it later.
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages'
            ),
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        }
    },
]

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'collectedstatic')
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

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


CRISPY_TEMPLATE_PACK = 'bootstrap3'


# OAUTH CONFIGURATION
# ------------------------------------------------------------------------------

LOGIN_URL = reverse_lazy('oauth_login')
LOGIN_REDIRECT_URL = reverse_lazy('users:home')

AUTHENTICATION_BACKENDS = (
    'TWLight.users.authorization.OAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
)

TWLIGHT_OAUTH_PROVIDER_URL = 'https://meta.wikimedia.org/w/index.php'

TWLIGHT_OAUTH_CONSUMER_KEY = os.environ.get('TWLIGHT_OAUTH_CONSUMER_KEY', None)
TWLIGHT_OAUTH_CONSUMER_SECRET = os.environ.get('TWLIGHT_OAUTH_CONSUMER_SECRET', None)



# COMMENTS CONFIGURATION
# ------------------------------------------------------------------------------


# TAGGIT CONFIGURATION
# ------------------------------------------------------------------------------
TAGGIT_CASE_INSENSITIVE = True


# REVERSION CONFIGURATION
# ------------------------------------------------------------------------------

# See https://django-reversion.readthedocs.org/ .

# We are NOT using reversion middleware, because that creates revisions when
# save() is called in the context of some http requests, but not on all database
# saves. This makes it untestable. Instead we decorate the Application.save().


# DJMAIL CONFIGURATION
# ------------------------------------------------------------------------------

EMAIL_BACKEND = 'djmail.backends.default.EmailBackend'

# This is a dummy backend that will write to stdout. Safe, yet useless.
DJMAIL_REAL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
INSTALLED_APPS += ('djmail',)


# DJANGO_REQUEST CONFIGURATION
# ------------------------------------------------------------------------------

MIDDLEWARE_CLASSES += ('request.middleware.RequestMiddleware',)

# The following are set for privacy purposes. Note that, if some amount of
# geographic tracking is desired, there is a REQUEST_ANONYMOUS_IP setting which
# scrubs the last octet of the IP address, which could be used instead of
# REQUEST_LOG_IP. There is not a way to get semi-granular user tracking (such
# as tracking only authenticated vs anonymous users).
REQUEST_LOG_IP = False
REQUEST_LOG_USER = False
