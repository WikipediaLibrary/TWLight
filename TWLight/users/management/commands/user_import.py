import csv
import json
import logging
import urllib2

from datetime import datetime
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from ....users.models import Editor,UserProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        # now do the things that you want with your models here
        user = models.OneToOneField(settings.AUTH_USER_MODEL)
        with open('/vagrant/TaylorAndFrancisUserData.csv') as f:
               reader = csv.reader(f)
               for row in reader:
                  if row[0] != '\xef\xbb\xbfPartner':
                     logger.info('importing {row}.'.format(row=row))
                     global_userinfo = self.get_global_userinfo_from_wp_username(row[2])
                     if global_userinfo:
                         # 2014-02-04T13:38:01Z
                         logger.info('{info}.'.format(info=global_userinfo))
                         reg_date = datetime.strptime(global_userinfo['registration'], '%Y-%m-%dT%H:%M:%SZ').date()
                         try:
                             logger.info("Found user.")
                             username = global_userinfo['id']
                             user = User.objects.get(username=username)
                             created = False
                         except User.DoesNotExist:
                             logger.info("Can't find user; creating one.")
                             user = User.objects.create_user(username=global_userinfo['id'], email=row[3])
                             created = True
    
                         if created:
                             try:
                                 Editor.objects.get_or_create(
                                     user_id = user.pk,
                                     wp_username = global_userinfo['name'],
                                     wp_sub = global_userinfo['id'],
                                     wp_editcount = global_userinfo['editcount'],
                                     wp_registered = reg_date
                                 )
                                 logger.info("Can't find editor; creating one.")
                             except:
                                 logger.exception("Unable to create {editor}.".format(editor=global_userinfo['name']))
                                 pass

    def get_global_userinfo_from_wp_username(self,wp_username):
        """
        Grab global user information from the API, which we'll use to overlay
        somme local wiki user info returned by OAuth.  Returns a dict like:

        global_userinfo:
          home:         "zhwikisource"
          id:           27666025
          registration: "2013-05-05T16:00:09Z"
          name:         "Example"
          editcount:    10
        """
        try:
            endpoint = '{base}/w/api.php?action=query&meta=globaluserinfo&guiuser={name}&guiprop=editcount&format=json&formatversion=2'.format(base='https://meta.wikimedia.org',name=urllib2.quote(wp_username))

            results = json.loads(urllib2.urlopen(endpoint).read())
            global_userinfo = results['query']['globaluserinfo']
            assert 'missing' not in global_userinfo
            logger.info('user_import fetched global_userinfo for User {info}.'.format(info=global_userinfo))
            return global_userinfo
        except:
            logger.exception('user_import could not fetch global_userinfo for {username}.'.format(username=urllib2.quote(wp_username)))
            return None
            pass
