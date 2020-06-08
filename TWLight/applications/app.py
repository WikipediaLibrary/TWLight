from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class Config(AppConfig):
    name = "TWLight.applications"
    verbose_name = _("applications")

    def ready(self):
        import TWLight.applications.signals
