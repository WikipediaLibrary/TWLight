import logging
from django.core.management.base import BaseCommand, CommandError
from TWLight.applications.models import Application
from TWLight.applications.signals import Reminder
from TWLight.applications.views import ListApplicationsView

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def add_arguments(self, parser):
       parser.add_argument('--app_status', type=str, required=True)

    def handle(self, *args, **options):
       if options['app_status'] == 'PENDING':
           pending_app_list = ListApplicationsView().get_queryset()
           for app in pending_app_list:
               Reminder.coordinator_reminder.send(sender=self.__class__, app=app)
