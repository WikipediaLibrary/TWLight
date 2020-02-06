import json
import logging
import urllib.request, urllib.error, urllib.parse

from django.utils.timezone import now
from django.core.management.base import BaseCommand
from TWLight.users.models import (
    Editor,
    editor_recent_edits,
    editor_bundle_eligible,
    editor_enough_edits,
    editor_valid,
)

logger = logging.getLogger(__name__)


# Everything here is largely lifted from the Editor model. An indicator that things should be refactored.


def get_global_userinfo(editor):
    endpoint = "{base}/w/api.php?action=query&meta=globaluserinfo&guiuser={name}&format=json&formatversion=2".format(
        base="https://meta.wikimedia.org", name=urllib.parse.quote(editor.wp_username)
    )

    results = json.loads(urllib.request.urlopen(endpoint).read())
    global_userinfo = results["query"]["globaluserinfo"]
    # If the user isn't found global_userinfo contains the empty key "missing"
    assert "missing" not in global_userinfo
    # Verify that the numerical account ID matches, not just the user's handle.
    assert editor.wp_sub == global_userinfo["id"]
    return global_userinfo


class Command(BaseCommand):
    def handle(self, **options):
        editors = Editor.objects.filter(wp_bundle_eligible=True)
        for editor in editors:
            global_userinfo = get_global_userinfo(editor)
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
                editor.wp_editcount_updated = now()
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
