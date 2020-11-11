from datetime import datetime, timedelta
import json
import logging
import typing
import urllib.request, urllib.error, urllib.parse
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def editor_global_userinfo(
    wp_username: str, wp_sub: typing.Optional[int], strict: bool
):
    """
    Public interface for fetching Editor global_userinfo.
    Parameters
    ----------
    wp_username : str
        Global Wikipedia username, used for guiuser parameter in globaluserinfo calls.
    wp_sub : int
        Global Wikipedia User ID, used for guiid parameter in globaluserinfo calls.
    strict : bool
        Verify that guiuser and guiid match. This precludes library account takeover via wikipedia username changes,
        but also precludes updates to accounts upon username change.

    Returns
    -------
    dict
        The editor's globaluserinfo as returned by the mediawiki api.
    """
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


def _get_user_info_request(wp_param_name: str, wp_param: str):
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
        The globaluserinfo api query response as described in the MediaWiki API globaluserinfo documentation:
        https://www.mediawiki.org/w/api.php?action=help&modules=query%2Bglobaluserinfo
    """
    endpoint = settings.TWLIGHT_API_PROVIDER_ENDPOINT
    query = "{endpoint}?action=query&meta=globaluserinfo&{wp_param_name}={wp_param}&guiprop=editcount|merged&format=json&formatversion=2".format(
        endpoint=endpoint, wp_param_name=wp_param_name, wp_param=wp_param
    )
    return json.loads(urllib.request.urlopen(query).read())


def editor_reg_date(identity: dict, global_userinfo: dict):
    """
    Normalize registration date from either oauth or global_userinfo as datetime.date object.
    Parameters
    ----------
    identity : dict
    global_userinfo : dict

    Returns
    -------
    datetime.date
    """
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
    """
    Check for Editor global editcount criterion.
    Parameters
    ----------
    editcount : int

    Returns
    -------
    bool
        Answer to the question: has the editor made at least 500 edits across all projects?
    """
    # If, for some reason, this information hasn't come through,
    # default to user not being valid.
    if not editcount:
        return False
    return editcount >= 500


def editor_not_blocked(merged: list):
    """
    Check for Editor "no blocks on any merged account" criterion.
    Parameters
    ----------
    merged : list
        A list of merged accounts for this Editor as returned by globaluserinfo.

    Returns
    -------
    bool
        Answer to the question: is the editor's free of blocks for all merged accounts?
    """
    # If, for some reason, this information hasn't come through,
    # default to user not being valid.
    if not merged:
        return False
    else:
        # Check: not blocked on any merged account.
        # Note that this looks funny since we're inverting the truthiness returned by the check for blocks.
        return False if any("blocked" in account for account in merged) else True


def editor_account_old_enough(wp_registered: datetime.date):
    """
    Check for Editor account age criterion.
    Parameters
    ----------
    wp_registered : datetime.date

    Returns
    -------
    bool
        Answer to the question: is the editor's account old enough?
    """
    # If, for some reason, this information hasn't come through,
    # default to user not being valid.
    if not wp_registered:
        return False
    # Check: registered >= 6 months ago
    return datetime.today().date() - timedelta(days=182) >= wp_registered


def editor_valid(
    enough_edits: bool,
    account_old_enough: bool,
    not_blocked: bool,
    ignore_wp_blocks: bool,
):
    """
    Check all eligibility criteria laid out in the terms of service.
    Note that we won't prohibit signups or applications on this basis.
    Coordinators have discretion to approve people who are near the cutoff.
    Parameters
    ----------
    enough_edits : bool
    account_old_enough : bool
    not_blocked : bool
    ignore_wp_blocks : bool

    Returns
    -------
    bool
        Answer to the question: is the editor account valid?
    """
    if enough_edits and account_old_enough and (not_blocked or ignore_wp_blocks):
        return True
    else:
        return False


def editor_recent_edits(
    global_userinfo_editcount: int,
    wp_editcount: int,
    wp_editcount_updated: datetime.date,
    wp_editcount_prev_updated: datetime.date,
    wp_editcount_prev: int,
    wp_editcount_recent: int,
    wp_enough_recent_edits: bool,
    current_datetime: timezone = None,
):
    """
    Checks current global_userinfo editcount against stored editor data and returns updated data.
    Parameters
    ----------
    global_userinfo_editcount : int
        editcount returned by globaluserinfo.
    wp_editcount : int
        editcount currently stored in database.
    wp_editcount_updated : datetime.date
        timestamp for stored editcount
    wp_editcount_prev_updated : datetime.date
        timestamp for stored previous editcount
    wp_editcount_prev : int
        historical editcount used to calculate recent edits
    wp_editcount_recent : int
        recent editcount used to determine bundle eligibility
    wp_enough_recent_edits : bool
        current recent edit status as stored in database
    current_datetime : timezone
        optional timezone-aware timestamp override that represents now()

    Returns
    -------
    tuple
        Contains recent-editcount-related results.
    """
    if not current_datetime:
        current_datetime = timezone.now()

    # If we have historical data that might let us fix eligibility issues, use wp_editcount_prev to do so.
    if (
        wp_editcount_prev
        and wp_editcount_prev_updated
        and (current_datetime - wp_editcount_prev_updated).days < 31
    ):
        editcount_update_delta = wp_editcount_updated - wp_editcount_prev_updated
        editcount_delta = global_userinfo_editcount - wp_editcount_prev
    # If we have normal historical data, see how many days have passed and how many edits have been made since the last check.
    elif wp_editcount and wp_editcount_updated:
        editcount_update_delta = current_datetime - wp_editcount_updated
        editcount_delta = global_userinfo_editcount - wp_editcount
    # If we don't have any historical editcount data, let all edits to date count
    else:
        editcount_update_delta = current_datetime - timedelta(days=31)
        editcount_delta = global_userinfo_editcount
        wp_editcount = global_userinfo_editcount
        wp_editcount_updated = current_datetime

    if (
        # If the editor didn't have enough recent edits but they do now, update the counts immediately.
        # This recognizes their eligibility as soon as possible.
        (not wp_enough_recent_edits and editcount_delta >= 10)
        # If the user had enough edits, just update the counts after 30 days.
        # This means that eligibility always lasts at least 30 days.
        or (wp_enough_recent_edits and editcount_update_delta.days > 30)
    ):
        # Shift the currently stored counts into the "prev" fields for use in future checks.
        wp_editcount_prev = wp_editcount
        wp_editcount_prev_updated = wp_editcount_updated
        wp_editcount_recent = editcount_delta

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


def editor_bundle_eligible(editor: "Editor"):
    """
    Checks all of the individual eligibility components to determine if Editor is eligible for Bundle.
    Note that the type hint is just the classname to avoid a circular import.
    Parameters
    ----------
    editor : Editor

    Returns
    -------
    bool
        Answer to the question: is the editor account eligible for Bundle?
    """
    enough_edits_and_valid = editor.wp_valid and editor.wp_enough_recent_edits
    # Staff and superusers should be eligible for bundles for testing purposes
    user_staff_or_superuser = editor.user.is_staff or editor.user.is_superuser
    # Users must accept the terms of use in order to be eligible for bundle access
    user_accepted_terms = editor.user.userprofile.terms_of_use
    if (enough_edits_and_valid or user_staff_or_superuser) and user_accepted_terms:
        return True
    else:
        return False
