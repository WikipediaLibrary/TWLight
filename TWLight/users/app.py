from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class Config(AppConfig):
    name = "TWLight.users"
    verbose_name = _("users")

    def ready(self):
        import TWLight.users.signals
