# -*- coding: utf-8 -*-
"""
Base settings for twlight project.

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
import json

# Importing global settings is typically not recommended, and un-Django-like,
# but we're doing something interesting with the LANGUAGES setting.
from django.conf.global_settings import LANGUAGES as GLOBAL_LANGUAGES
from django.contrib import messages

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

# Import available locales from Faker, so we can determine what languages we fake in tests.
from faker.config import AVAILABLE_LOCALES as FAKER_AVAILABLE_LOCALES

# We're going to replace Django's default logging config.
import logging.config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TWLIGHT_HOME = os.path.dirname(
    os.path.dirname(os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir)))
)

# An atypical way of setting django languages for TranslateWiki integration:
# https://translatewiki.net/wiki/Thread:Support/_The_following_issue_is_unconfirmed,_still_to_be_investigated._Adding_TheWikipediaLibrary_Card_Platform_TranslateWiki

# Returns the intersectional language codes between Django and Wikimedia CLDR
# along with the language autonyms from Wikimedia CLDR.
# https://github.com/wikimedia/language-data
def get_django_cldr_languages_intersection(dir):
    languages_intersection = []
    language_data_json = open(os.path.join(dir, "language-data.json"))
    languages = json.loads(language_data_json.read())["languages"]
    for lang_code, lang_data in languages.items():
        for i, (djlang_code, djlang_name) in enumerate(GLOBAL_LANGUAGES):
            if lang_code == djlang_code:
                autonym = lang_data[-1]
                languages_intersection += [(lang_code, autonym)]
    return sorted(set(languages_intersection))


# Get the language codes from the locale directories, and compare them to the
# intersecting set of languages between Django and Wikimedia CLDR.
# Use langauge autonyms from Wikimedia.
def get_languages_from_locale_subdirectories(dir):
    current_languages = []
    languages_intersection = INTERSECTIONAL_LANGUAGES
    for locale_dir in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, locale_dir)):
            for i, (lang_code, autonym) in enumerate(languages_intersection):
                if locale_dir == lang_code:
                    current_languages += [(lang_code, autonym)]
    return sorted(set(current_languages))


# Get the intersection of available Faker locales and the specified language set.
def get_django_faker_languages_intersection(languages):
    languages_intersection = []
    for locale in FAKER_AVAILABLE_LOCALES:
        for i, (djlang_code, djlang_name) in enumerate(languages):
            # Exclude common English locales from random test selection; English often works while others are broken.
            if (
                locale == djlang_code
                and locale != "en"
                and locale != "en_US"
                and locale != "en_GB"
            ):
                languages_intersection += [locale]
    return sorted(set(languages_intersection))


# ------------------------------------------------------------------------------
# ------------------------> core django configurations <------------------------
# ------------------------------------------------------------------------------

# APP CONFIGURATION
# ------------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",  # Not a django app; replaces staticfiles
    "django.contrib.staticfiles",
    "django.contrib.sites",  # required by django.contrib.comments
]

THIRD_PARTY_APPS = [
    "annoying",
    "crispy_forms",
    "reversion",
    "dal",
    "dal_select2",
    "django_comments",
    "django_cron",
    "django_filters",
    "modeltranslation",
    "taggit",
    # DO NOT CONFUSE THIS with requests, the Python URL library! This is
    # django-request, the user analytics package.
    "request",
    "django_countries",
    "rest_framework",
    "rest_framework.authtoken",
]

TWLIGHT_APPS = [
    "TWLight.i18n",
    "TWLight.users",
    "TWLight.resources",
    "TWLight.applications",
    "TWLight.emails",
    "TWLight.graphs",
    "TWLight.comments",
    "TWLight.api",
    "TWLight.ezproxy",
]

# dal (autocomplete_light) and modeltranslation must go before django.contrib.admin.
INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + TWLIGHT_APPS

# CRON CONFIGURATION
# ------------------------------------------------------------------------------
CRON_CLASSES = [
    "TWLight.crons.BackupCronJob",
    "TWLight.crons.SendCoordinatorRemindersCronJob",
    "TWLight.crons.UserRenewalNoticeCronJob",
    "TWLight.crons.ProxyWaitlistDisableCronJob",
]

# REST FRAMEWORK CONFIG
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning"
}

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------

MIDDLEWARE_CLASSES = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise should be loaded before everything but security.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # LocaleMiddleware must go after Session (and Cache, if used), but before
    # Common.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.SessionAuthenticationMiddleware",
    # The default storage backend relies on sessions.
    # That’s why SessionMiddleware must be enabled and appear before
    # MessageMiddleware.
    "django.contrib.messages.middleware.MessageMiddleware",
]


# DEBUG
# ------------------------------------------------------------------------------

# By setting this an an environment variable, it is easy to switch debug on in
# servers to do a quick test.
# DEBUG SHOULD BE FALSE ON PRODUCTION for security reasons.

DEBUG = bool(os.environ.get("DEBUG", "False").lower() == "true")

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

# WMF sysadmins strongly prefer mysql, so use that.
# If you're deploying to Heroku, heroku.py will override this.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DJANGO_DB_NAME", None),
        "USER": os.environ.get("DJANGO_DB_USER", None),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", None),
        "HOST": os.environ.get("DJANGO_DB_HOST", None),
        "PORT": "3306",
        # This is critical for handling Unicode data due to stupid properties
        # of MySQL; see https://stackoverflow.com/questions/2108824/mysql-incorrect-string-value-error-when-save-unicode-string-in-django .
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_ALL_TABLES'; SET storage_engine='INNODB';",
        },
    }
}


# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# In production, this list should contain the URL of the server and nothing
# else, for security reasons. For local testing '*' is OK.
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost 127.0.0.1 [::1]").split(" ")

# Let Django know about external URLs in case they differ from internal
# Needed to be added for /admin
USE_X_FORWARDED_HOST = True

REQUEST_BASE_URL = os.environ.get("REQUEST_BASE_URL", None)

ROOT_URLCONF = "TWLight.urls"

WSGI_APPLICATION = "TWLight.wsgi.application"

SITE_ID = 1

# Overwrite messages.ERROR to use danger instead, to play nice with bootstrap
MESSAGE_TAGS = {messages.ERROR: "danger"}


# INTERNATIONALIZATION CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = "en"  # Sets site default language.

# https://django-modeltranslation.readthedocs.io/en/latest/installation.html#advanced-settings

MODELTRANSLATION_DEFAULT_LANGUAGE = (
    LANGUAGE_CODE
)  # sets the modeltranslation default language.

LOCALE_PATHS = [
    # makemessages looks for locale/ in the top level, not the project level.
    os.path.join(os.path.dirname(BASE_DIR), "locale")
]

# We're letting the file-based translation contributions dictate the languages
# available to the system. This keeps our column and index count for db-stored
# translations as low as possible while allowing translatewiki contributions to
# be used without reconfiguring the site.
INTERSECTIONAL_LANGUAGES = get_django_cldr_languages_intersection(LOCALE_PATHS[0])
LANGUAGES = get_languages_from_locale_subdirectories(LOCALE_PATHS[0])
FAKER_LOCALES = get_django_faker_languages_intersection(INTERSECTIONAL_LANGUAGES)

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "OPTIONS": {
            # Reiterating the default so we can add to it later.
            "context_processors": (
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ),
            # We cache templates by default.
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                )
            ],
        },
    }
]

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "collectedstatic")
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# MEDIA FILE CONFIGURATION
# ------------------------------------------------------------------------------

# https://docs.djangoproject.com/en/1.8/topics/files/

MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "media")
MEDIA_URL = "/media/"


# ------------------------------------------------------------------------------
# -----------------> third-party and TWLight configurations <-------------------
# ------------------------------------------------------------------------------


CRISPY_TEMPLATE_PACK = "bootstrap3"


# EZPROXY CONFIGURATION
# ------------------------------------------------------------------------------
TWLIGHT_EZPROXY_URL = os.environ.get("TWLIGHT_EZPROXY_URL", None)
TWLIGHT_EZPROXY_SECRET = os.environ.get("TWLIGHT_EZPROXY_SECRET", None)

# OAUTH CONFIGURATION
# ------------------------------------------------------------------------------

LOGIN_URL = reverse_lazy("oauth_login")
LOGIN_REDIRECT_URL = reverse_lazy("users:home")

AUTHENTICATION_BACKENDS = [
    "TWLight.users.oauth.OAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

TWLIGHT_OAUTH_PROVIDER_URL = os.environ.get("TWLIGHT_OAUTH_PROVIDER_URL", None)

TWLIGHT_OAUTH_CONSUMER_KEY = os.environ.get("TWLIGHT_OAUTH_CONSUMER_KEY", None)
TWLIGHT_OAUTH_CONSUMER_SECRET = os.environ.get("TWLIGHT_OAUTH_CONSUMER_SECRET", None)

# API CONFIGURATION
# ------------------------------------------------------------------------------

TWLIGHT_API_PROVIDER_ENDPOINT = os.environ.get("TWLIGHT_API_PROVIDER_ENDPOINT", None)

# COMMENTS CONFIGURATION
# ------------------------------------------------------------------------------
COMMENTS_APP = "TWLight.comments"

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

DJMAIL_REAL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_BACKEND = "djmail.backends.async.EmailBackend"
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = 25
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False

INSTALLED_APPS += ["djmail"]


# DJANGO_REQUEST CONFIGURATION
# ------------------------------------------------------------------------------

MIDDLEWARE_CLASSES += ["request.middleware.RequestMiddleware"]

# The following are set for privacy purposes. Note that, if some amount of
# geographic tracking is desired, there is a REQUEST_ANONYMOUS_IP setting which
# scrubs the last octet of the IP address, which could be used instead of
# REQUEST_LOG_IP. There is not a way to get semi-granular user tracking (such
# as tracking only authenticated vs anonymous users).
REQUEST_LOG_IP = False
REQUEST_LOG_USER = False

# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
# We're replacing the default logging config to get better control of the
# mail_admins behavior.

ADMINS = [("TWLight Developers", "librarycard-dev@lists.wikimedia.org")]
DJANGO_EMAIL_ADMINS_BACKEND = os.environ.get(
    "DJANGO_EMAIL_ADMINS_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
LOGGING_CONFIG = None

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
            "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
        },
        "formatters": {
            "django.server": {
                "()": "django.utils.log.ServerFormatter",
                "format": "[%(server_time)s] %(message)s",
            }
        },
        "handlers": {
            "nodebug_console": {
                "level": "WARNING",
                "filters": ["require_debug_false"],
                "class": "logging.StreamHandler",
            },
            "debug_console": {
                "level": "INFO",
                "filters": ["require_debug_true"],
                "class": "logging.StreamHandler",
            },
            "django.server": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "django.server",
            },
            "mail_admins": {
                "level": "ERROR",
                "filters": ["require_debug_false"],
                "class": "django.utils.log.AdminEmailHandler",
                "email_backend": DJANGO_EMAIL_ADMINS_BACKEND,
            },
        },
        "loggers": {
            "django": {
                "handlers": ["nodebug_console", "debug_console", "mail_admins"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            },
            "django.server": {
                "handlers": ["django.server"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
                "propagate": False,
            },
            "TWLight": {
                "handlers": ["nodebug_console", "debug_console", "mail_admins"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            },
        },
    }
)
