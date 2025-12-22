# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from TWLight.emails.models import Message


class Command(BaseCommand):
    help = "Delete draft emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subject",
            type=str,
            required=True,
            help="Email subject",
        )
        parser.add_argument(
            "--userprofile_flag_field",
            type=str,
            help="Optionally unset userprofile boolean that tracks sent status for messages with the specified subject",
        )

    def handle(self, *args, **options):
        subject = options["subject"]
        userprofile_flag_field = options["userprofile_flag_field"]

        Message.objects.bulk_cleanup_drafts(
            subject=subject, userprofile_flag_field=userprofile_flag_field
        )
