from django.apps import AppConfig

class Config(AppConfig):
    name = "TWLight.users"
    verbose_name = "users"

    def ready(self):
        import TWLight.users.signals
