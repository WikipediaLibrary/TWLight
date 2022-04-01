from datetime import date, datetime, timedelta
import json
import logging
import os
import urllib.request, urllib.error, urllib.parse
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password

from djmail import template_mail

logger = logging.getLogger(__name__)


def editor_global_userinfo(wp_sub: int):
    """
    Public interface for fetching Editor global_userinfo.
    Parameters
    ----------
    wp_sub : int
        Global Wikipedia User ID, used for guiid parameter in globaluserinfo calls.

    Returns
    -------
    dict
        The editor's globaluserinfo as returned by the mediawiki api.
    """
    try:
        # Try to get global user info with wp_sub
        results = _get_user_info_request("guiid", str(wp_sub))
        global_userinfo = results["query"]["globaluserinfo"]
        # If the user isn't found global_userinfo contains the empty key "missing"
        if "missing" in global_userinfo:
            global_userinfo = None
    # If we don't get a response with the expected keys, something else went awry.
    except KeyError:
        global_userinfo = None
    if global_userinfo is None:
        logger.exception(f"Could not fetch global_userinfo for User {wp_sub}")
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

    reg_dates = []
    # Try oauth registration date.
    try:
        reg_dates.append(
            datetime.strptime(identity["registered"], "%Y%m%d%H%M%S").date()
        )
    except (TypeError, ValueError):
        pass
    # Try global_userinfo date
    try:
        reg_dates.append(
            datetime.strptime(
                global_userinfo["registration"], "%Y-%m-%dT%H:%M:%SZ"
            ).date()
        )
    except (TypeError, ValueError):
        pass

    # List sorting is a handy way to get the oldest date.
    reg_dates.sort()
    reg_date = reg_dates[0]

    # If we got a date, return it.
    if isinstance(reg_date, date):
        return reg_date
    # If we got something unexpected, return None.
    else:
        return None


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
    if wp_registered is None:
        return False
    # Check: registered >= 6 months ago
    return date.today() - timedelta(days=182) >= wp_registered


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
    wp_bundle_eligible = (
        enough_edits_and_valid or user_staff_or_superuser
    ) and user_accepted_terms
    # Except for special users that we use for load testing
    ignore_wp_bundle_eligible = editor.ignore_wp_bundle_eligible
    if wp_bundle_eligible or ignore_wp_bundle_eligible:
        return True
    else:
        return False


def editor_make_block_dict(merged: list):
    """
    Creates a hash based on a JSON string of a user's blocks
    ----------
    merged : list
        A list of merged accounts for this Editor as returned by globaluserinfo.

    Returns
    -------
    str
        A sorted JSON string of a user's blocks
    """
    blocked_dict = {}
    for account in merged:
        if "blocked" in account:
            blocked_dict[account["wiki"]] = account["blocked"]

    # Sort by key
    sorted_blocked_dict = dict(sorted(blocked_dict.items(), key=lambda k: k[0]))

    return str(sorted_blocked_dict)


class BlockHashChangedEmail(template_mail.TemplateMail):
    name = "block_hash_changed"


def editor_compare_hashes(
    previous_block_hash: str,
    new_block_string: str,
    wp_username: str,
    ignore_wp_blocks: bool,
):
    """
    Compares two block hashes. If they are different, it means an editor's block status
    has changed and email is sent to the team to check it.
    ----------
    previous_block_hash : str
        The value of the previous block hash.
    new_block_string: str
        The recently generated block dictionary without hashing.
    wp_username: str
        The Wikipedia username of the editor we are comparing block hashes from
    ignore_wp_blocks: bool
        Flag that indicates whether a block is overruled for access to the library

    Returns
    -------
    str
        An updated hash of the JSON string of a user's blocks if there are any changes.
        If not, the previous hash will be reassigned to new_block_string
    """
    if previous_block_hash != "":
        if not check_password(new_block_string, previous_block_hash):
            # Hash does not match, checking if a user has the block override
            if ignore_wp_blocks:
                # Send email to TWL team
                email = BlockHashChangedEmail()
                email.send(
                    os.environ.get(
                        "TWLIGHT_ERROR_MAILTO", "wikipedialibrary@wikimedia.org"
                    ),
                    {"wp_username": wp_username},
                )

            return make_password(new_block_string)
        else:
            return previous_block_hash
    else:
        # previous_block_hash is blank, we will make a hash of the user's
        # block string.
        return make_password(new_block_string)
