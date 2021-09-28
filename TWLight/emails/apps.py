from django.apps import AppConfig


class EmailConfig(AppConfig):
    name = "TWLight.emails"
    label = "emails"

    def ready(self):
        """
        # We have to import signal receivers upon initialization or they won't
        # be registered at the proper time by Django, and then the signals will
        # not be received, and emails won't get sent, and there will be nothing
        # but a lone and level field of yaks stretching far away...
        """
        from . import tasks
