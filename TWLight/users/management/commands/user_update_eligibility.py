from datetime import datetime

import logging


from django.utils.timezone import now
from django.core.management.base import BaseCommand
from TWLight.users.models import Editor

from TWLight.users.helpers.editor_data import (
    editor_global_userinfo,
    editor_valid,
    editor_enough_edits,
    editor_recent_edits,
    editor_bundle_eligible,
)

logger = logging.getLogger(__name__)


# Everything here is largely lifted from the Editor model. An indicator that things should be refactored.


class Command(BaseCommand):
    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        wp_editcount_updated = now()
        if options["datetime"]:
            wp_editcount_updated = datetime.fromisoformat(options["datetime"])

        editors = Editor.objects.filter(wp_bundle_eligible=True)
        for editor in editors:
            if options["global_userinfo"]:
                global_userinfo = options["global_userinfo"]
            else:
                global_userinfo = editor_global_userinfo(
                    editor.wp_username, editor.wp_sub, True
                )
            if global_userinfo:
                editor.wp_editcount_prev_updated, editor.wp_editcount_prev, editor.wp_editcount_recent, editor.wp_enough_recent_edits = editor_recent_edits(
                    global_userinfo["editcount"],
                    editor.wp_editcount_updated,
                    editor.wp_editcount,
                    editor.wp_editcount_prev_updated,
                    editor.wp_editcount_prev,
                    editor.wp_editcount_recent,
                    editor.wp_enough_recent_edits,
                )
                editor.wp_editcount = global_userinfo["editcount"]
                editor.wp_editcount_updated = wp_editcount_updated
                editor.wp_enough_edits = editor_enough_edits(global_userinfo)
                editor.wp_valid = editor_valid(
                    editor.wp_enough_edits,
                    # We could recalculate this, but we would only need to do that if upped the minimum required account age.
                    editor.wp_account_old_enough,
                    # editor.wp_not_blocked can only be rechecked on login, so we're going with the existing value.
                    editor.wp_not_blocked,
                )
                editor.wp_bundle_eligible = editor_bundle_eligible(
                    editor.wp_valid, editor.wp_enough_recent_edits
                )
                editor.save()
