from django.apps import AppConfig


class Config(AppConfig):
    name = "TWLight.resources"
    label = "resources"
    verbose_name = "resources"

    def ready(self):
        import TWLight.resources.signals
