# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.db.models import DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate
from django.utils.timezone import timedelta
from django.utils.translation import gettext_lazy as _

from TWLight.emails.models import Message
from TWLight.emails.tasks import send_survey_active_user_email
from TWLight.users.groups import get_restricted

logger = logging.getLogger(__name__)


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
        # Validate the lang args
        survey_langs = options["lang"]
        valid_langs = []
        invalid_langs = []
        for lang_code, _lang_name in settings.LANGUAGES:
            valid_langs.append(lang_code)

        for survey_lang in survey_langs:
            if survey_lang not in valid_langs:
                invalid_langs.append(survey_lang)

        if invalid_langs:
            raise CommandError(
                "invalid lang argument in list: {}".format(invalid_langs)
            )

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
                # meet the block criterion or are exempt
                Q(editor__wp_not_blocked=True) | Q(editor__ignore_wp_blocks=True),
                # have an non-wikimedia.org email address
                Q(email__isnull=False)
                & ~Q(email="")
                & ~Q(email__endswith="@wikimedia.org"),
                # meet the 6 month criterion as of last login or are exempt
                Q(last_login_age__gte=timedelta(days=182))
                | Q(editor__ignore_wp_account_age_requirement=True),
                # meet the 500 edit criterion or are exempt
                Q(editor__wp_enough_edits=True)
                | Q(editor__ignore_wp_edit_requirement=True),
                # are 'active'
                is_active=True,
            )
        )
        logger.info("{} users qualify".format(users.count()))
        previously_sent_user_pks = Message.twl.user_pks_with_subject_list(
            # Translators: email subject line
            subject=_("The Wikipedia Library needs your help!"),
            users=users,
        )
        logger.info(
            "{} users previously sent message will be skipped".format(
                len(previously_sent_user_pks)
            )
        )
        users = (
            users.exclude(pk__in=previously_sent_user_pks)
            .distinct()
            .order_by("last_login")
        )
        logger.info("{} remaining users qualify".format(users.count()))
        users = users[:batch_size]
        logger.info("attempting to send to {} users".format(users.count()))

        # Use a single connection to send all emails
        connection = get_connection(backend=backend)
        connection.open()

        # send the emails
        for user in users:
            try:
                send_survey_active_user_email(
                    sender=self.__class__,
                    backend=backend,  # allows setting the djmail backend back to default for testing
                    connection=connection,  # passing in the connection lets us handle these in bulk
                    user_email=user.email,
                    user_lang=user.userprofile.lang,
                    survey_id=options["survey_id"],
                    survey_langs=survey_langs,
                )
            except Exception as e:
                logger.error(e)

        connection.close()
