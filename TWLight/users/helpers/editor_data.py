from datetime import datetime, timedelta
import json
import logging
import typing
import urllib.request, urllib.error, urllib.parse
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


def editor_global_userinfo(
    wp_username: str, wp_sub: typing.Optional[int], strict: bool
):
    endpoint = settings.TWLIGHT_OAUTH_PROVIDER_URL + "/w/api.php"
    guiuser = urllib.parse.quote(wp_username)
    query = "{endpoint}?action=query&meta=globaluserinfo&guiuser={guiuser}&guiprop=editcount|merged&format=json&formatversion=2".format(
        endpoint=endpoint, guiuser=guiuser
    )

    results = json.loads(urllib.request.urlopen(query).read())
    """
    Expected data:
    {
    "batchcomplete": true,
     "query": {
        "globaluserinfo": {                         # Global account
            "home": "enwiki",                           # Wiki used to determine the name of the global account. See https://www.mediawiki.org/wiki/SUL_finalisation
            "id": account['id'],                        # Wikipedia ID
            "registration": "YYYY-MM-DDTHH:mm:ssZ",     # Date registered
            "name": account['name'],                    # wikipedia username
            "merged": [                                 # Individual project accounts attached to the global account.
                {
                    "wiki": "enwiki",
                    "url": "https://en.wikipedia.org",
                    "timestamp": "YYYY-MM-DDTHH:mm:ssZ",
                    "method": "login",
                    "editcount": account['editcount']           # editcount for this project
                    "registration": "YYYY-MM-DDTHH:mm:ssZ",     # Date registered for this project
                    "groups": ["extendedconfirmed"],
                    "blocked": {                                # Only exists if the user has blocks for this project.
                    "expiry": "infinity",
                    "reason": ""
                }
                ... # Continues ad nauseam
            ],
            "editcount": account['editcount']           # global editcount
        }
     }
    }
    """

    try:
        global_userinfo = results["query"]["globaluserinfo"]
        # If the user isn't found global_userinfo contains the empty key "missing"
        assert "missing" not in global_userinfo
        if strict:
            # Verify that the numerical account ID matches, not just the user's handle.
            assert isinstance(wp_sub, int)
            assert wp_sub == global_userinfo["id"]
    except (KeyError, AssertionError):
        global_userinfo = None
        logger.exception("Could not fetch global_userinfo for User.")
    return global_userinfo


def editor_reg_date(identity, global_userinfo):
    # Try oauth registration date first.  If it's not valid, try the global_userinfo date
    try:
        reg_date = datetime.strptime(identity["registered"], "%Y%m%d%H%M%S").date()
    except (TypeError, ValueError):
        try:
            reg_date = datetime.strptime(
                global_userinfo["registration"], "%Y-%m-%dT%H:%M:%SZ"
            ).date()
        except (TypeError, ValueError):
            reg_date = None
    return reg_date


def editor_enough_edits(editcount: int):
    # If, for some reason, this information hasn't come through,
    # default to user not being valid.
    if not editcount:
        return False
    return editcount >= 500


def editor_not_blocked(merged: list):
    # If, for some reason, this information hasn't come through,
    # default to user not being valid.
    if not merged:
        return False
    else:
        # Check: not blocked on any merged account.
        # Note that this looks funny since we're inverting the truthiness returned by the check for blocks.
        return False if any("blocked" in account for account in merged) else True


def editor_account_old_enough(wp_registered):
    # If, for some reason, this information hasn't come through,
    # default to user not being valid.
    if not wp_registered:
        return False
    # Check: registered >= 6 months ago
    return datetime.today().date() - timedelta(days=182) >= wp_registered


def editor_valid(enough_edits, account_old_enough, not_blocked, ignore_wp_blocks):
    """
    Check for the eligibility criteria laid out in the terms of service.
    Note that we won't prohibit signups or applications on this basis.
    Coordinators have discretion to approve people who are near the cutoff.
    """
    if enough_edits and account_old_enough and (not_blocked or ignore_wp_blocks):
        return True
    else:
        return False


def editor_recent_edits(
    global_userinfo_editcount,
    wp_editcount_updated,
    wp_editcount,
    wp_editcount_prev_updated,
    wp_editcount_prev,
    wp_editcount_recent,
    wp_enough_recent_edits,
):

    # If we have historical data, see how many days have passed and how many edits have been made since the last check.
    if wp_editcount_prev_updated and wp_editcount_updated:
        editcount_update_delta = now() - wp_editcount_prev_updated
        editcount_delta = global_userinfo_editcount - wp_editcount_prev
        if (
            # If the editor didn't have enough recent edits but they do now, update the counts immediately.
            # This recognizes their eligibility as soon as possible.
            (not wp_enough_recent_edits and editcount_delta >= 10)
            # If the user had enough edits, just update the counts after 30 days.
            # This means that eligibility always lasts at least 30 days.
            or (wp_enough_recent_edits and editcount_update_delta.days > 30)
        ):
            wp_editcount_prev = wp_editcount
            wp_editcount_prev_updated = wp_editcount_updated
            wp_editcount_recent = global_userinfo_editcount - wp_editcount_prev

    # If we don't have any historical editcount data, let all edits to date count.
    # Editor.wp_editcount_prev defaults to 0, so we don't need to worry about changing it.
    else:
        wp_editcount_prev_updated = now()
        wp_editcount_recent = global_userinfo_editcount

    # Perform the check for enough recent edits.
    if wp_editcount_recent >= 10:
        wp_enough_recent_edits = True
    else:
        wp_enough_recent_edits = False
    # Return a tuple containing all recent-editcount-related results.
    return (
        wp_editcount_prev_updated,
        wp_editcount_prev,
        wp_editcount_recent,
        wp_enough_recent_edits,
    )


def editor_bundle_eligible(wp_valid, wp_enough_recent_edits):
    if wp_valid and wp_enough_recent_edits:
        return True
    else:
        return False
