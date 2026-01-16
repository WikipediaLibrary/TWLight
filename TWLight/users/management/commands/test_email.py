# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from TWLight.users.signals import TestEmail


class Command(BaseCommand):
    help = "Sends testmail to a wikipedia editor."

    def add_arguments(self, parser):
        parser.add_argument(
            "wp_username",
            type=str,
            help="The wikipedia editor to send the test email to",
        )

    def handle(self, *args, **options):
        user = User.objects.select_related("editor").get(
            editor__wp_username=options["wp_username"]
        )
        TestEmail.test.send(
            sender=self.__class__,
            wp_username=user.editor.wp_username,
            email=user.email,
        )
