from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from TWLight.users.signals import ProjectPage2021Launch
from TWLight.users.models import Editor


class Command(BaseCommand):
    help = (
        "Sends emails to active editors notifying them of the 2021 project page rollout."
    )

    def handle(self, *args, **options):
        active_authorized_editors = Editor.objects.filter(
            user__last_login__gt=timezone.now() - timedelta(days=90),
            user__authorization__isnull=False,
        )
        for editor in active_authorized_editors:
            # Ensure we didn't already send this user an email.
            if not editor.user.userprofile.proxy_notification_sent:
                ProjectPage2021Launch.launch_notice.send(
                    sender=self.__class__,
                    user_wp_username=editor.wp_username,
                    user_email=editor.user.email,
                )
                editor.user.userprofile.project_page_2021_notification_sent = True
                editor.user.userprofile.save()
