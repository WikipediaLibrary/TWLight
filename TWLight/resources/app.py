from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class Config(AppConfig):
    name = "TWLight.resources"
    verbose_name = _("resources")

    def ready(self):
        import TWLight.resources.signals
