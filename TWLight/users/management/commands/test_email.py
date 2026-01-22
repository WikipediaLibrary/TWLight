# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.mail import get_connection
from django.core.management.base import BaseCommand

from TWLight.emails.tasks import send_test


class Command(BaseCommand):
    help = "Sends testmail to a wikipedia editor."

    def add_arguments(self, parser):
        parser.add_argument(
            "wp_username",
            type=str,
            help="The wikipedia editor to send the test email to",
        )
        parser.add_argument(
            "--backend",
            type=str,
            required=False,
            help="djmail backend to use; default is TWLight.emails.backends.mediawiki.EmailBackend",
        )

    def handle(self, *args, **options):
        user = User.objects.select_related("editor").get(
            editor__wp_username=options["wp_username"]
        )
        backend = (
            options["backend"]
            if options["backend"]
            else "TWLight.emails.backends.mediawiki.EmailBackend"
        )
        # Use a single connection to send all emails
        connection = get_connection(backend=backend)
        connection.open()
        send_test(
            sender=self.__class__,
            backend=backend,  # allows setting the djmail backend back to default for testing
            connection=connection,  # passing in the connection lets us handle these in bulk
            wp_username=user.editor.wp_username,
            email=user.email,
        )
        connection.close()
