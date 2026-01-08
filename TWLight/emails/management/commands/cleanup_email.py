# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from TWLight.emails.models import Message


class Command(BaseCommand):
    help = "Delete unsent emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subject",
            type=str,
            required=False,
            help="Email subject",
        )

    def handle(self, *args, **options):
        subject = options["subject"]

        if subject is None:
            Message.twl.unsent().delete()
        else:
            Message.twl.filter(subject=subject).unsent().delete()
