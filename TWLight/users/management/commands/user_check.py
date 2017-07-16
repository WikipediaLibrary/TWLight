import json
import logging
import urllib2

from datetime import datetime
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from ....users.models import Editor,UserProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, **options):
        editors = Editor.objects.all()
        for editor in editors:
            global_userinfo = self.get_global_userinfo(editor)
            try:
                assert editor.wp_sub == global_userinfo['id']
                #self.stdout.write(u'ID match for {name}: local ID: {twlight_sub} remote ID: {sul_id}'.format(name=urllib2.quote(editor.wp_username),twlight_sub=editor.wp_sub,sul_id=global_userinfo['id']))
            except AssertionError:
                self.stdout.write(u'ID mismatch for {name}: local ID: {twlight_sub} remote ID: {sul_id}'.format(name=urllib2.quote(editor.wp_username),twlight_sub=editor.wp_sub,sul_id=global_userinfo['id']))
                pass
            except:
                pass

    def get_global_userinfo(self, editor):
        try:
            endpoint = '{base}/w/api.php?action=query&meta=globaluserinfo&guiuser={name}&format=json&formatversion=2'.format(base='https://meta.wikimedia.org',name=urllib2.quote(editor.wp_username))

            results = json.loads(urllib2.urlopen(endpoint).read())
            global_userinfo = results['query']['globaluserinfo']
            # If the user isn't found global_userinfo contains the empty key
            # "missing"
            assert 'missing' not in global_userinfo
            return global_userinfo
        except:
            self.stdout.write(u'could not fetch global_userinfo for django user #{editor_id}.'.format(editor_id=str(editor.id)))
            return None
            pass
