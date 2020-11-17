from datetime import datetime, timedelta
import logging
from django.utils.timezone import now
from django.core.management.base import BaseCommand
from TWLight.users.models import Editor

from TWLight.users.helpers.editor_data import (
    editor_global_userinfo,
    editor_valid,
    editor_enough_edits,
    editor_recent_edits,
    editor_not_blocked,
    editor_bundle_eligible,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates editor info and Bundle eligibility for currently-eligible Editors."

    def add_arguments(self, parser):
        """
        Adds `datetime` and `global_userinfo` arguments.
        """
        parser.add_argument(
            "--datetime",
            action="store",
            help="ISO datetime used for calculating eligibility. Defaults to now. Currently only used for backdating command runs in tests.",
        )
        parser.add_argument(
            "--global_userinfo",
            action="store",
            help="specify Wikipedia global_userinfo data. Defaults to fetching live data. Currently only used for faking command runs in tests.",
        )
        parser.add_argument(
            "--timedelta_days",
            action="store",
            help="Number of days used to define 'recent' edits. Defaults to 30. Currently only used for faking command runs in tests.",
        )

    def handle(self, *args, **options):
        """
        Updates editor info and Bundle eligibility for currently-eligible Editors.
        Parameters
        ----------
        args
        options

        Returns
        -------
        None
        """

        # Default behavior is to use current datetime for timestamps.
        now_or_datetime = now()
        datetime_override = None
        timedelta_days = 30

        # This may be overridden so that values may be treated as if they were valid for an arbitrary datetime.
        if options["datetime"]:
            datetime_override = now_or_datetime.fromisoformat(options["datetime"])
            now_or_datetime = datetime_override

        if options["timedelta_days"]:
            timedelta_days = int(options["timedelta_days"])

        # Get all editors who have not been updated in more than 30 days.
        editors = Editor.objects.filter(
            wp_editcount_updated__lt=now_or_datetime - timedelta(days=timedelta_days)
        )
        for editor in editors:
            # `global_userinfo` data may be overridden.
            if options["global_userinfo"]:
                global_userinfo = options["global_userinfo"]
            # Default behavior is to fetch live `global_userinfo`
            else:
                global_userinfo = editor_global_userinfo(
                    editor.wp_username, editor.wp_sub, True
                )
            if global_userinfo:
                # Determine recent editcount.
                (
                    editor.wp_editcount_prev_updated,
                    editor.wp_editcount_prev,
                    editor.wp_editcount_recent,
                    editor.wp_enough_recent_edits,
                ) = editor_recent_edits(
                    global_userinfo["editcount"],
                    editor.wp_editcount,
                    editor.wp_editcount_updated,
                    editor.wp_editcount_prev_updated,
                    editor.wp_editcount_prev,
                    editor.wp_editcount_recent,
                    editor.wp_enough_recent_edits,
                    datetime_override,
                )
                # Set current editcount.
                editor.wp_editcount = global_userinfo["editcount"]
                editor.wp_editcount_updated = now_or_datetime
                # Determine editor validity.
                editor.wp_enough_edits = editor_enough_edits(editor.wp_editcount)
                editor.wp_not_blocked = editor_not_blocked(global_userinfo["merged"])
                editor.wp_valid = editor_valid(
                    editor.wp_enough_edits,
                    # We could recalculate this, but we would only need to do that if upped the minimum required account age.
                    editor.wp_account_old_enough,
                    # editor.wp_not_blocked can only be rechecked on login, so we're going with the existing value.
                    editor.wp_not_blocked,
                    editor.ignore_wp_blocks,
                )
                # Determine Bundle eligibility.
                editor.wp_bundle_eligible = editor_bundle_eligible(editor)
                # Save editor.
                editor.save()
                # Update bundle authorizations.
                editor.update_bundle_authorization()
