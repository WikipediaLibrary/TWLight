import csv
import django.conf
import json
import logging
import urllib.request, urllib.error, urllib.parse

from datetime import datetime
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from TWLight.users.models import Editor
from TWLight.users.helpers.editor_data import editor_global_userinfo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Imports users from applications CSV. Only looks at the Username, Email, and Timestamp fields.
    Fields:
    Partner [not used],
    Timestamp [optional] (date: dd/mm/yyyy),
    Username (string: wp_username),
    Email (string: user@example.com),
    Collection [not used],
    Title [not used]
    """

    # Let's not send mails about imported stuff.
    django.conf.settings.EMAIL_BACKEND = (
        "django.core.mail.backends.console.EmailBackend"
    )

    # Input file really needs to be UTF-8 encoded. We should do some sort of
    # assertion for that.

    def add_arguments(self, parser):
        parser.add_argument("file")

    def handle(self, *args, **options):
        user = models.OneToOneField(settings.AUTH_USER_MODEL)
        with open(options["file"]) as f:
            reader = csv.reader(f)
            # Skip first row, we expect it to be a header.
            next(reader, None)  # skip the headers
            for row in reader:
                wp_username = self.normalize_wp_username(row[2])
                # We're wrapping this whole thing in a redundant-looking try
                # block to avoid hitting the API unnecessarily.
                try:
                    editor = Editor.objects.get(wp_username=wp_username)
                    logger.info("Editor exists. Skipping import")
                except:
                    # TODO: Run import check to see if this actually works.
                    global_userinfo = editor_global_userinfo(wp_username, None, False)
                    if global_userinfo:
                        logger.info("{info}.".format(info=global_userinfo))
                        reg_date = datetime.strptime(
                            global_userinfo["registration"], "%Y-%m-%dT%H:%M:%SZ"
                        ).date()

                        try:
                            username = global_userinfo["id"]
                            user = User.objects.get(username=username)
                            created = False
                            logger.info("User exists.")
                        except User.DoesNotExist:
                            logger.info("Can't find user; creating one.")
                            user = User.objects.create_user(
                                username=global_userinfo["id"], email=row[3]
                            )
                            created = True

                        if created:
                            # Inconsistent date format on the input files
                            try:
                                date_created = datetime.strptime(
                                    row[1], "%d/%m/%Y %H:%M"
                                ).date()
                            except:
                                try:
                                    date_created = datetime.strptime(
                                        row[1], "%d/%m/%Y %H:%M:%S"
                                    ).date()
                                except:
                                    date_created = datetime.strptime(
                                        "01/01/1971 00:00:01", "%d/%m/%Y %H:%M:%S"
                                    ).date()

                            try:
                                Editor.objects.get_or_create(
                                    user_id=user.pk,
                                    wp_username=global_userinfo["name"],
                                    wp_sub=global_userinfo["id"],
                                    wp_editcount=global_userinfo["editcount"],
                                    wp_registered=reg_date,
                                    wp_valid=True,
                                    date_created=date_created,
                                )
                                logger.info("Can't find editor; creating one.")
                            except:
                                logger.exception(
                                    "Unable to create {editor}.".format(
                                        editor=global_userinfo["name"]
                                    )
                                )
                                pass
                    pass

    # Cribbed from stack overflow
    # https://stackoverflow.com/a/32232764
    # WP Usernames are uppercase and have spaces, not underscores
    def normalize_wp_username(self, wp_username):
        wp_username = wp_username.strip()
        wp_username = wp_username.replace("_", " ")
        wp_username = wp_username[0].upper() + wp_username[1:]

        return wp_username
