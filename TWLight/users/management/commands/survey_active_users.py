# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.mail import get_connection
from django.core.management.base import BaseCommand
from django.db.models import DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate
from django.utils.timezone import timedelta

from TWLight.users.groups import get_restricted
from TWLight.users.signals import Survey


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
        parser.add_argument(
            "--staff_test",
            action="store_true",
            required=False,
            help="Email only staff users who qualify other than staff status",
        )
        parser.add_argument(
            "--batch_size",
            type=int,
            required=False,
            help="number of emails to send; default is 1000",
        )
        parser.add_argument(
            "--backend",
            type=str,
            required=False,
            help="djmail backend to use; default is TWLight.emails.backends.mediawiki.EmailBackend",
        )

    def handle(self, *args, **options):
        # default mode excludes users who are staff or superusers
        role_filter = Q(is_staff=False) & Q(is_superuser=False)

        batch_size = options["batch_size"] if options["batch_size"] else 1000
        backend = (
            options["backend"]
            if options["backend"]
            else "TWLight.emails.backends.mediawiki.EmailBackend"
        )

        # test mode excludes users who are not staff and ignores superuser status
        if options["staff_test"]:
            role_filter = Q(is_staff=True)

        # All Wikipedia Library users who:
        users = (
            User.objects.select_related("editor", "userprofile")
            .annotate(
                # calculate account age at last login
                last_login_age=ExpressionWrapper(
                    TruncDate(F("last_login")) - F("editor__wp_registered"),
                    output_field=DurationField(),
                )
            )
            .filter(
                # meet the mode-dependent role requirements
                role_filter,
                # have not restricted data processing
                ~Q(groups__name__in=[get_restricted()]),
                # meet the block criterion or have the 'ignore wp blocks' exemption
                Q(editor__wp_not_blocked=True) | Q(editor__ignore_wp_blocks=True),
                # have an non-wikimedia.org email address
                Q(email__isnull=False)
                & ~Q(email="")
                & ~Q(email__endswith="@wikimedia.org"),
                # have not already received the email
                userprofile__survey_email_sent=False,
                # meet the 6 month criterion as of last login
                last_login_age__gte=timedelta(days=182),
                # meet the 500 edit criterion
                editor__wp_enough_edits=True,
                # are 'active'
                is_active=True,
            )
            .order_by("last_login")[:batch_size]
        )

        # No users qualify; exit
        if not users.exists():
            return

        connection = get_connection(backend=backend)
        connection.open()

        # send the emails
        for user in users:
            Survey.survey_active_user.send(
                sender=self.__class__,
                backend=backend,  # allows setting the djmail backend back to default for testing
                connection=connection,  # passing in the connection lets us handle these in bulk
                user_email=user.email,
                user_lang=user.userprofile.lang,
                survey_id=options["survey_id"],
                survey_langs=options["lang"],
            )

        connection.close()

        # Record that we sent the email so that we only send one.
        # user.userprofile.survey_email_sent = True
        # user.userprofile.save()
