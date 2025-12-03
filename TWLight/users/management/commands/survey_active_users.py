from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Prefetch, Q
from django.urls import reverse

from TWLight.users.groups import get_restricted
from TWLight.users.signals import Survey
from TWLight.users.models import Editor


class Command(BaseCommand):
    help = "Sends survey invitation email to active users."

    def add_arguments(self, parser):
        parser.add_argument(
            "survey_id", type=int, help="ID number for corresponding survey"
        )
        parser.add_argument(
            "lang",
            nargs="+",
            type=str,
            help="List of localized language codes for this survey",
        )

    def handle(self, *args, **options):
        # restricted users are "inactive"
        restricted = get_restricted()

        # All Wikipedia Library users who:
        for user in User.objects.select_related("editor", "userprofile").filter(
            # are 'active'
            ~Q(groups__name__in=[restricted]),
            # meet the block criterion or have the 'ignore wp blocks' exemption
            Q(editor__wp_not_blocked=True) | Q(editor__ignore_wp_blocks=True),
            # have an non-wikimedia.org email address
            Q(email__isnull=False) & ~Q(email__endswith="@wikimedia.org"),
            # have not already received the email
            userprofile__survey_email_sent=False,
            # meet the 6 month criterion
            editor__wp_account_old_enough=True,
            # meet the 500 edit criterion
            editor__wp_enough_edits=True,
            # are not staff
            is_staff=False,
            # are not superusers
            is_superuser=False,
        ):
            Survey.survey_active_user.send(
                sender=self.__class__,
                user_email=user.email,
                user_lang=user.userprofile.lang,
                survey_id=options["survey_id"],
                survey_langs=options["lang"],
            )

            # Record that we sent the email so that we only send one.
            user.userprofile.survey_email_sent = True
            user.userprofile.save()
