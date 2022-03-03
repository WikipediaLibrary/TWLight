from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Prefetch, Q
from django.urls import reverse

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.signals import Notice
from TWLight.users.models import Authorization, get_company_name, Editor


class Command(BaseCommand):
    help = "Sends advance notice to users with expiring authorizations, prompting them to apply for renewal."

    def handle(self, *args, **options):
        # Get all authorization objects with an expiry date in the next
        # four weeks, for which we haven't yet sent a reminder email, and
        # exclude users who disabled these emails and who have already filed
        # for a renewal.
        editor_qs = Editor.objects.select_related("user")
        applications_for_renewal = (
            Application.objects.prefetch_related(Prefetch("editor", queryset=editor_qs))
            .values("editor__user__pk", "partner__pk")
            .filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status__in=[Application.PENDING, Application.QUESTION],
                parent__isnull=False,
                editor__isnull=False,
            )
            .order_by("-date_created")
        )

        user_qs = User.objects.select_related("userprofile")
        expiring_authorizations = (
            Authorization.objects.prefetch_related(Prefetch("user", queryset=user_qs))
            .filter(
                date_expires__lt=datetime.today() + timedelta(weeks=2),
                date_expires__gte=datetime.today(),
                reminder_email_sent=False,
                partners__isnull=False,
            )
            .exclude(user__userprofile__send_renewal_notices=False)
        )

        # Create a list of authorizations that already have a renewal application
        no_email_list = []
        for application in applications_for_renewal:
            no_email_list.append(
                expiring_authorizations.values_list("pk").filter(
                    partners=application["partner__pk"],
                    user=application["editor__user__pk"],
                )
            )

        # Iterate through all expiring authorizations except the ones that have
        # a renewal
        for authorization_object in expiring_authorizations.exclude(
            pk__in=no_email_list
        ):
            Notice.user_renewal_notice.send(
                sender=self.__class__,
                user_wp_username=authorization_object.user.editor.wp_username,
                user_email=authorization_object.user.email,
                user_lang=authorization_object.user.userprofile.lang,
                partner_name=get_company_name(authorization_object),
                partner_link=reverse("users:my_library"),
            )

            # Record that we sent the email so that we only send one.
            authorization_object.reminder_email_sent = True
            authorization_object.save()
