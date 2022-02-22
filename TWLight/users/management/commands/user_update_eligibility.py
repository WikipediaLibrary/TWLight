from datetime import timedelta
import logging
from django.utils.timezone import now
from django.core.management.base import BaseCommand
from TWLight.users.models import Editor

from TWLight.users.helpers.editor_data import (
    editor_global_userinfo,
    editor_valid,
    editor_enough_edits,
    editor_not_blocked,
    editor_bundle_eligible,
    editor_account_old_enough,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates editor info and Bundle eligibility for currently-eligible Editors."

    def add_arguments(self, parser):
        """
        Adds command arguments.
        """
        parser.add_argument(
            "--datetime",
            action="store",
            help="ISO datetime used for calculating eligibility. Defaults to now. Currently only used for backdating command runs in tests.",
        )
        parser.add_argument(
            "--global_userinfo",
            action="store",
            help="Specify Wikipedia global_userinfo data. Defaults to fetching live data. Currently only used for faking command runs in tests.",
        )
        parser.add_argument(
            "--timedelta_days",
            action="store",
            help="Number of days used to define 'recent' edits. Defaults to 30. Currently only used for faking command runs in tests.",
        )
        parser.add_argument(
            "--wp_username",
            action="store",
            help="Specify a single editor to update. Other arguments and filters still apply.",
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

        # Default behavior is to use current datetime for timestamps to check all editors.
        now_or_datetime = now()
        datetime_override = None
        timedelta_days = 0
        wp_username = None
        editors = Editor.objects.all()

        # This may be overridden so that values may be treated as if they were valid for an arbitrary datetime.
        # This is also passed to the model method.
        if options["datetime"]:
            datetime_override = now_or_datetime.fromisoformat(options["datetime"])
            now_or_datetime = datetime_override

        # These are used to limit the set of editors updated by the command.
        # Nothing is passed to the model method.
        if options["timedelta_days"]:
            timedelta_days = int(options["timedelta_days"])

        # Get editors that haven't been updated in the specified time range, with an option to limit on wp_username.
        if timedelta_days:
            editors = editors.exclude(
                editorlogs__timestamp__gt=now_or_datetime
                - timedelta(days=timedelta_days),
            )

        # Optional wp_username filter.
        if options["wp_username"]:
            editors = editors.filter(wp_username=str(options["wp_username"]))

        # Iterator reduces memory footprint for large querysets
        for editor in editors.iterator():
            # T296853: avoid stale editor data while looping through big sets.
            editor.refresh_from_db()
            # `global_userinfo` data may be overridden.
            if options["global_userinfo"]:
                global_userinfo = options["global_userinfo"]
                editor.check_sub(global_userinfo["id"])
            # Default behavior is to fetch live `global_userinfo`
            else:
                global_userinfo = editor_global_userinfo(editor.wp_sub)
            if global_userinfo:
                editor.update_editcount(global_userinfo["editcount"], datetime_override)
                # Determine editor validity.
                editor.wp_enough_edits = editor_enough_edits(editor.wp_editcount)
                editor.wp_not_blocked = editor_not_blocked(global_userinfo["merged"])
                # We will only check if the account is old enough if the value is False
                # Accounts that are already old enough will never cease to be old enough
                if not editor.wp_account_old_enough:
                    editor.wp_account_old_enough = editor_account_old_enough(
                        editor.wp_registered
                    )
                editor.wp_valid = editor_valid(
                    editor.wp_enough_edits,
                    editor.wp_account_old_enough,
                    # editor.wp_not_blocked can only be rechecked on login, so we're going with the existing value.
                    editor.wp_not_blocked,
                    editor.ignore_wp_blocks,
                )
                # Determine Bundle eligibility.
                editor.wp_bundle_eligible = editor_bundle_eligible(editor)
                # Save editor.
                editor.save()
                # Prune EditorLogs, with daily_prune_range set to only check the previous day to improve performance.
                editor.prune_editcount(
                    current_datetime=datetime_override, daily_prune_range=2
                )
                # Update bundle authorizations.
                editor.update_bundle_authorization()
