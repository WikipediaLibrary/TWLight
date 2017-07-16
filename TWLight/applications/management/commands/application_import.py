import csv
import django.conf
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
    # Let's not send mails about imported stuff.
    django.conf.settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
                       # If the collections field is empty, make it a list containing an empty string.
                       if row[4] in (None, ""):
                           specific_stream_ids = ['']
                       # Otherwise try to split it on comma
                       else:
                           specific_stream_ids = row[4].split(',')

                       # If the title field is empty, make it a list containing an empty string.
                       if row[5] in (None, ""):
                           specific_titles = ['']
                       # Otherwise try to split it on semicolon
                       else:
                           specific_titles = row[5].split(';')

                       for specific_stream_id in specific_stream_ids:

                           for specific_title in specific_titles:

                               # Where possible we're fetching the objects attached
                               # to our attributes to verify they already exist.

                               partner_id = row[0]
                               partner = Partner.objects.get(pk=partner_id)

                               # Inconsistent date format on the input files
                               # If the date field is empty, set it to the beginning of (Unix) time.
                               if row[1] in (None, ""):
                                   datetime_created = datetime.strptime('01/01/1970 00:00:00', '%d/%m/%Y %H:%M:%S')

                               # If we have a date field
                               else:
                                   # Try fetching the most precise timestamp
                                   try:
                                       datetime_created = datetime.strptime(row[1], '%d/%m/%Y %H:%M:%S')

                                   except ValueError:
                                       # If that doesn't work, try getting a less precise timestamp
                                       try:
                                           datetime_created = datetime.strptime(row[1], '%d/%m/%Y %H:%M')

                                       except ValueError:
                                           # If that doesn't work, try getting a date
                                           try:
                                               datetime_created = datetime.strptime(row[1], '%d/%m/%Y')
                                           except:
                                               pass

                               date_created = datetime_created

                               wp_username = self.normalize_wp_username(row[2])
                               editor = Editor.objects.get(wp_username=wp_username)
                               editor_id = editor.pk

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
                                       specific_title = specific_title,
                                       imported = True,
                                       status = 4
                                   )
                               except Application.DoesNotExist:
                                   application = Application(
                                       partner_id = partner_id,
                                       date_created = date_created,
                                       date_closed = date_created,
                                       editor_id = editor_id,
                                       specific_stream_id = specific_stream_id,
                                       specific_title = specific_title,
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
                       logger.exception("Unable to create {wp_username}'s application to {partner_id}.".format(wp_username=self.normalize_wp_username(row[2]),partner_id=row[0]))
                       pass

    # Cribbed from stack overflow
    # https://stackoverflow.com/a/32232764
    # WP Usernames are uppercase and have spaces, not underscores
    def normalize_wp_username(self, wp_username):
        wp_username = wp_username.strip()
        wp_username = wp_username.replace('_', ' ')
        wp_username = wp_username[0].upper() + wp_username[1:]

        return wp_username
