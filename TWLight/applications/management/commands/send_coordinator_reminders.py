import logging
from django.core.management.base import BaseCommand, CommandError
from TWLight.applications.signals import Reminder

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def add_arguments(self, parser):
       parser.add_argument('--app_status', type=str, required=True)

    def handle(self, *args, **options):
       Reminder.coordinator_reminder.send(sender=self.__class__, app_status=options['app_status'])
