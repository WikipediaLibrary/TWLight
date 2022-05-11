from django.apps import AppConfig


class MiddlewareConfig(AppConfig):
    name = "TWLight.common"
    label = "common"

    def ready(self):
        import TWLight.common.middleware
