import json
import logging
import urllib2

from datetime import datetime
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from ....users.models import Editor, UserProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, **options):
        users = User.objects.all()
        for user in users:
            try:
                assert hasattr(user, "editor")
            except AssertionError:
                self.stdout.write(
                    u"{username}: no editor object.".format(username=(user.username))
                )
                # Move on to the next user
                continue

            try:
                global_userinfo = self.get_global_userinfo(user)
                assert user.editor.wp_sub == global_userinfo["id"]
            except AssertionError:
                self.stdout.write(
                    u"{name}: ID mismatch - local ID: {twlight_sub} remote ID: {sul_id}".format(
                        name=user.editor.wp_username,
                        twlight_sub=user.editor.wp_sub,
                        sul_id=global_userinfo["id"],
                    )
                )
                pass
            except:
                pass

    def get_global_userinfo(self, user):
        try:
            endpoint = "{base}/w/api.php?action=query&meta=globaluserinfo&guiuser={name}&format=json&formatversion=2".format(
                base="https://meta.wikimedia.org",
                name=urllib2.quote(user.editor.wp_username.encode("utf-8")),
            )

            results = json.loads(urllib2.urlopen(endpoint).read())
            global_userinfo = results["query"]["globaluserinfo"]
            # If the user isn't found global_userinfo contains the empty key
            # "missing"
            assert "missing" not in global_userinfo
            return global_userinfo
        except:
            self.stdout.write(
                u"{username}:{wp_username}: could not fetch global_userinfo.".format(
                    username=str(
                        user.username,
                        wp_username=user.editor.wp_username.encode("utf-8"),
                    )
                )
            )
            return None
            pass
