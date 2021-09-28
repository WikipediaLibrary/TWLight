from django.apps import AppConfig


class Config(AppConfig):
    name = "TWLight.applications"
    label = "applications"
    verbose_name = "applications"

    def ready(self):
        import TWLight.applications.signals
