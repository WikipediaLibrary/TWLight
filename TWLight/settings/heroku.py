import sys

from .base import *

# Parse database configuration from $DATABASE_URL
import dj_database_url

DATABASES["default"] = dj_database_url.config()

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Allow all host headers
ALLOWED_HOSTS = ["*"]


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "brief": {
            "format": "%(asctime)s %(levelname)s %(name)s[%(funcName)s]: %(message)s"
        }
    },
    "handlers": {
        "console_info": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
        }
    },
    "loggers": {"": {"handlers": ["console_info"], "level": "INFO"}},
}
