import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from TWLight.users.helpers.editor_data import editor_global_userinfo

logger = logging.getLogger(__name__)

# TODO: Check if the assertion inside editor_global_userinfo bubbles up to this command.


class Command(BaseCommand):
    def handle(self, **options):
        users = User.objects.all()
        for user in users:
            try:
                assert hasattr(user, "editor")
            except AssertionError:
                self.stdout.write(
                    "{username}: no editor object.".format(username=(user.username))
                )
                # Move on to the next user
                continue
            try:
                global_userinfo = editor_global_userinfo(
                    user.editor.wp_username, user.editor.wp_sub, True
                )
            except AssertionError:
                self.stdout.write(
                    "{name}: ID mismatch - local ID: {twlight_sub} remote ID: {sul_id}".format(
                        name=user.editor.wp_username,
                        twlight_sub=user.editor.wp_sub,
                        sul_id=global_userinfo["id"],
                    )
                )
