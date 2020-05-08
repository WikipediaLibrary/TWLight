from django.core.management.base import BaseCommand

from TWLight.users.signals import ProxyBundleLaunch
from TWLight.users.models import User


class Command(BaseCommand):
    help = "Sends emails to all users notifying them of the Proxy/Bundle rollout."

    def handle(self, *args, **options):
        all_users = User.objects.all()
        for user in all_users:
            # Ensure we didn't already send this user an email.
            if not user.userprofile.proxy_notification_sent:
                ProxyBundleLaunch.launch_notice.send(
                    sender=self.__class__,
                    user_wp_username=user.editor.wp_username,
                    user_email=user.email,
                )
                user.userprofile.proxy_notification_sent = True
                user.userprofile.save()
