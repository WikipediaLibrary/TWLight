import csv
import logging

from datetime import date, datetime
from django.utils.timezone import now
from django.db import models
from django.core.management.base import BaseCommand, CommandError
from reversion import revisions as reversion
from reversion.models import Version
from ....users.models import Editor
from ....applications.models import Application
from ....resources.models import Partner, Stream

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    # Input file really needs to be UTF-8 encoded. We should do some sort of
    # assertion for that.

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        with open(options['file']) as f:
               reader = csv.reader(f)
               # Skip first row, we expect it to be a header.
               next(reader, None)  # skip the headers
               for row in reader:
                   try:
                       try:
                           specific_stream_ids = row[4].split(',')
                       except:
                           specific_stream_ids = ['']
                       for specific_stream_id in specific_stream_ids:
                           # Where possible we're fetching the objects attaChed
                           # to our attributes to verify they already exist.

                           partner_id = row[0]
                           partner = Partner.objects.get(pk=partner_id)

                           # Inconsistent date format on the input files
                           try:
                               datetime_created = datetime.strptime(row[1], '%m/%d/%Y %H:%M')
                           except:
                               try:
                                   datetime_created = datetime.strptime(row[1], '%m/%d/%Y %H:%M:%S')
                               except:
                                   #datetime_created = now
                                   date_created = datetime.strptime('01/01/1971 00:00:01', '%m/%d/%Y %H:%M:%S').date()

                           date_created = datetime_created

                           wp_username = row[2]
                           editor = Editor.objects.get(wp_username=wp_username)
                           editor_id = editor.pk

                           specific_stream_id = row[4]
                           try:
                               stream = Stream.objects.get(pk=specific_stream_id)
                           except:
                               specific_stream_id = None
                               stream = None

                           import_note = 'Imported on ' + str(date.today()) + '.'

                           try:
                               application = Application.objects.get(
                                   partner_id = partner_id,
                                   date_created = date_created,
                                   date_closed = date_created,
                                   editor_id = editor_id,
                                   specific_stream_id = specific_stream_id,
                                   status = 4
                               )
                           except Application.DoesNotExist:
                               application = Application(
                                   partner_id = partner_id,
                                   date_created = date_created,
                                   date_closed = date_created,
                                   editor_id = editor_id,
                                   specific_stream_id = specific_stream_id,
                                   comments = import_note,
                                   rationale = import_note,
                                   imported = True,
                                   status = 4
                               )
                               with reversion.create_revision():
                                   reversion.set_date_created(datetime_created)
                                   application.save()
                                   logger.info("Application created.")
                   except:
                       logger.exception("Unable to create {wp_username}'s application to {partner_id}.".format(wp_username=row[2],partner_id=row[0]))
                       pass
