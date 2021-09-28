from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from TWLight.users.signals import SearchLaunch2021
from TWLight.users.models import Authorization, Editor
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Sends an email to all users to let them know that the search feature has launched."

    def handle(self, *args, **options):
        editors = Editor.objects.all()
        for editor in editors:
            SearchLaunch2021.launch_notice.send(
                sender=self.__class__,
                user_wp_username=editor.wp_username,
                user_email=editor.user.email,
                lang=editor.user.userprofile.lang,
            )
