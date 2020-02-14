from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.urls import reverse

from TWLight.users.signals import Notice
from TWLight.users.models import Authorization


class Command(BaseCommand):
    help = "Sends advance notice to users with expiring authorizations, prompting them to apply for renewal."

    def handle(self, *args, **options):
        # Get all authorization objects with an expiry date in the next
        # four weeks, for which we haven't yet sent a reminder email, and
        # exclude users who disabled these emails.
        expiring_authorizations = Authorization.objects.filter(
            date_expires__lt=datetime.today() + timedelta(weeks=4),
            date_expires__gte=datetime.today(),
            reminder_email_sent=False,
        ).exclude(user__userprofile__send_renewal_notices=False)

        for authorization_object in expiring_authorizations:
            Notice.user_renewal_notice.send(
                sender=self.__class__,
                user_wp_username=authorization_object.user.editor.wp_username,
                user_email=authorization_object.user.email,
                user_lang=authorization_object.user.userprofile.lang,
                partner_name=authorization_object.partner.company_name,
                partner_link=reverse("users:my_library"),
            )

            # Record that we sent the email so that we only send one.
            authorization_object.reminder_email_sent = True
            authorization_object.save()
