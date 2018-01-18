import logging
import django.dispatch
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)
send_coordinator_reminders = django.dispatch.Signal(providing_args=['app_status'])

class Command(BaseCommand):

    def add_arguments(self, parser):
       parser.add_argument('app_status', nargs='+', type=str)

    def handle(self, *args, **options):
       send_coordinator_reminders.send(sender=self, app_status=options['app_status']) 
