import csv
import logging

from datetime import date, datetime
from django.db import models
from django.core.management.base import BaseCommand, CommandError
from ....users.models import Editor
from ....applications.models import Application
from ....resources.models import Partner, Stream

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        with open(options['file']) as f:
               reader = csv.reader(f)
               # Skip first row, we expect it to be a header.
               next(reader, None)  # skip the headers
               for row in reader:
                   try:
                       # Where possible we're fetching the objects attaChed
                       # to our attributes to verify they already exist.

                       partner_id = row[0]
                       partner = Partner.objects.get(pk=partner_id)

                       # Inconsistent date format on the input files
                       try:
                           date_created = datetime.strptime(row[1], '%m/%d/%Y %H:%M').date()
                       except:
                           date_created = datetime.strptime(row[1], '%m/%d/%Y %H:%M:%S').date()

                       wp_username=row[2]
                       editor = Editor.objects.get(wp_username=wp_username)
                       editor_id = editor.pk

                       specific_stream_id = row[4]
                       stream = Stream.objects.get(pk=specific_stream_id)
                       import_note = 'Imported on ' + str(date.today()) + '.'

                       Application.objects.get_or_create(
                           partner_id = partner_id,
                           date_created = date_created,
                           date_closed = date_created,
                           editor_id = editor_id,
                           specific_stream_id = specific_stream_id,
                           comments = import_note,
                           rationale = import_note,
                           status = 4
                       )
                       logger.info("Application created.")
                   except:
                       logger.exception("Unable to create {wp_username}'s application to {partner_id}.".format(wp_username=row[2],partner_id=row[0]))
                       pass
