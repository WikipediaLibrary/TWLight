import csv
import json
import logging
import urllib2

from datetime import datetime
from django.utils.timezone import now
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from ....users.models import Editor,UserProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    # Input file really needs to be UTF-8 encoded. We should do some sort of
    # assertion for that.

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        user = models.OneToOneField(settings.AUTH_USER_MODEL)
        with open(options['file']) as f:
               reader = csv.reader(f)
               # Skip first row, we expect it to be a header.
               next(reader, None)  # skip the headers
               for row in reader:
                   wp_username = row[2]
                   # We're wrapping this whole thing in a redundant-looking try
                   # block to avoid hitting the API unnecessarily.
                   try:
                       editor = Editor.objects.get(wp_username=wp_username)
                       logger.info("Editor exists. Skipping import")
                   except:
                       global_userinfo = self.get_global_userinfo_from_wp_username(wp_username)
                       if global_userinfo:
                           logger.info('{info}.'.format(info=global_userinfo))
                           reg_date = datetime.strptime(global_userinfo['registration'], '%Y-%m-%dT%H:%M:%SZ').date()

                           try:
                               username = global_userinfo['id']
                               user = User.objects.get(username=username)
                               created = False
                               logger.info("User exists.")
                           except User.DoesNotExist:
                               logger.info("Can't find user; creating one.")
                               user = User.objects.create_user(
                                   username=global_userinfo['id'],
                                   email=row[3]
                               )
                               created = True
    
                           if created:
                               # Inconsistent date format on the input files
                               try:
                                   date_created = datetime.strptime(row[1], '%m/%d/%Y %H:%M').date()
                               except:
                                   try:
                                       date_created = datetime.strptime(row[1], '%m/%d/%Y %H:%M:%S').date()
                                   except:
                                       #date_created = now
                                       date_created = datetime.strptime('01/01/1971 00:00:01', '%m/%d/%Y %H:%M:%S').date()

                               try:
                                   Editor.objects.get_or_create(
                                       user_id = user.pk,
                                       wp_username = global_userinfo['name'],
                                       wp_sub = global_userinfo['id'],
                                       wp_editcount = global_userinfo['editcount'],
                                       wp_registered = reg_date,
                                       wp_valid = True,
                                       date_created = date_created,
                                       last_updated = date_created
                                   )
                                   logger.info("Can't find editor; creating one.")
                               except:
                                   logger.exception("Unable to create {editor}.".format(editor=global_userinfo['name']))
                                   pass
                       pass

    def get_global_userinfo_from_wp_username(self,wp_username):
        try:
            endpoint = '{base}/w/api.php?action=query&meta=globaluserinfo&guiuser={name}&guiprop=editcount&format=json&formatversion=2'.format(base='https://meta.wikimedia.org',name=urllib2.quote(wp_username))

            results = json.loads(urllib2.urlopen(endpoint).read())
            global_userinfo = results['query']['globaluserinfo']
            # If the user isn't found global_userinfo contains the empty key
            # "missing"
            assert 'missing' not in global_userinfo
            logger.info('fetched global_userinfo for user')
            return global_userinfo
        except:
            logger.exception('could not fetch global_userinfo for {username}.'.format(username=urllib2.quote(wp_username)))
            return None
            pass
