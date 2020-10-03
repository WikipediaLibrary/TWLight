from django.core.management.base import BaseCommand

from TWLight.users.signals import ProxyBundleLaunch
from TWLight.users.models import Editor


class Command(BaseCommand):
    help = "Sends emails to all editors notifying them of the Proxy/Bundle rollout."

    def handle(self, *args, **options):
        all_editors = Editor.objects.all()
        for editor in all_editors:
            # Ensure we didn't already send this user an email.
            if not editor.user.userprofile.proxy_notification_sent:
                ProxyBundleLaunch.launch_notice.send(
                    sender=self.__class__,
                    user_wp_username=editor.wp_username,
                    user_email=editor.user.email,
                )
                editor.user.userprofile.proxy_notification_sent = True
                editor.user.userprofile.save()
