from django.core.management.base import BaseCommand

from TWLight.users.signals import ProxyBundleLaunch
from TWLight.users.models import User


class Command(BaseCommand):
    help = "Sends emails to all users notifying them of the Proxy/Bundle rollout, and drops active user sessions."

    def handle(self, *args, **options):
        all_users = User.objects.all()
        for user in all_users:
            ProxyBundleLaunch.launch_notice.send(
                sender=self.__class__,
                user_wp_username=user.editor.wp_username,
                user_email=user.email,
            )
