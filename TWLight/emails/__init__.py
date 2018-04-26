# Moved from importing recievers in __init__.py to AppConfig when upgrading to
# Django 1.9. The old way called the app registry before it finished loading.
# That is no longer supported in Django 1.9.

default_app_config = 'TWLight.emails.apps.EmailConfig'
