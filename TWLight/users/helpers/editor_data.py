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
    guiuser = urllib.parse.quote(wp_username)
    # Trying to get global user info with the username
    results = _get_user_info_request("guiuser", guiuser)

    try:
        global_userinfo = results["query"]["globaluserinfo"]
        # If the user isn't found global_userinfo contains the empty key "missing"
        if "missing" in global_userinfo:
            # querying again, this time using wp_sub
            results = _get_user_info_request("guiid", wp_sub)
            global_userinfo = results["query"]["globaluserinfo"]
        if strict:
            # Verify that the numerical account ID matches, not just the user's handle.
            assert isinstance(wp_sub, int)
            assert wp_sub == global_userinfo["id"]
    except (KeyError, AssertionError):
        global_userinfo = None
        logger.exception(f"Could not fetch global_userinfo for User {guiuser}")
    return global_userinfo


def _get_user_info_request(wp_param_name, wp_param):
    """
    This function queries the mediawiki api to get users' Wikipedia information

    Parameters
    ----------
    wp_param_name : str
        The name of the parameter we want to query by. Can be guiuser or guiid
    wp_param : str
        The value of that parameter we want to query by wp_username or wp_sub.

    Returns
    -------
    dict
        A dictionary like the one below or a dictionary with a "missing" key

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
    endpoint = settings.TWLIGHT_API_PROVIDER_ENDPOINT
    query = "{endpoint}?action=query&meta=globaluserinfo&{wp_param_name}={wp_param}&guiprop=editcount|merged&format=json&formatversion=2".format(
        endpoint=endpoint, wp_param_name=wp_param_name, wp_param=wp_param
    )
    return json.loads(urllib.request.urlopen(query).read())


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
            wp_editcount_recent = global_userinfo_editcount - wp_editcount_prev
            wp_editcount_prev = global_userinfo_editcount
            wp_editcount_prev_updated = wp_editcount_updated

    # If we don't have any historical editcount data, let all edits to date count
    else:
        wp_editcount_prev = global_userinfo_editcount
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


def editor_bundle_eligible(editor):
    enough_edits_and_valid = editor.wp_valid and editor.wp_enough_recent_edits
    # Staff and superusers should be eligible for bundles for testing purposes
    user_staff_or_superuser = editor.user.is_staff or editor.user.is_superuser
    # Users must accept the terms of use in order to be eligible for bundle access
    user_accepted_terms = editor.user.userprofile.terms_of_use
    if (enough_edits_and_valid or user_staff_or_superuser) and user_accepted_terms:
        return True
    else:
        return False
