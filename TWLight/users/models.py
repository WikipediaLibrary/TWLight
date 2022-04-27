# -*- coding: utf-8 -*-

"""
This file holds user profile information. (The base User model is part of
Django; profiles extend that with locally useful information.)

TWLight has three user types:
* editors
* coordinators
* site administrators.

_Editors_ are Wikipedia editors who are applying for TWL resource access
grants. We track some of their data here to facilitate access grant
decisions.

_Coordinators_ are the Wikipedians who have responsibility for evaluating
and deciding on access grants. Site administrators should add editors to the
Coordinators group through the Django admin site.

_Site administrators_ have admin privileges for this site. They have no special
handling in this file; they are handled through the native Django is_admin
flag, and site administrators have responsibility for designating who has that
flag through the admin site.

New users who sign up via oauth will be created as editors. Site administrators
may promote them to coordinators manually in the Django admin site, by adding
them to the coordinators group. They can also directly create Django user
accounts without attached Editors in the admin site, but this has no current
use case.
"""

from datetime import datetime, date, timedelta
import json
import logging
import urllib.request, urllib.error, urllib.parse
from annoying.functions import get_object_or_None
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import (
    MultipleObjectsReturned,
    SuspiciousOperation,
    ValidationError,
)
from django.urls import reverse
from django.db import models
from django.db.models import Q
from django.db.models.signals import m2m_changed
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from TWLight.resources.models import Partner
from TWLight.users.groups import get_coordinators
from TWLight.users.helpers.validation import validate_partners, validate_authorizer

from TWLight.users.helpers.editor_data import (
    editor_global_userinfo,
    editor_valid,
    editor_account_old_enough,
    editor_enough_edits,
    editor_not_blocked,
    editor_reg_date,
    editor_bundle_eligible,
    editor_make_block_dict,
    editor_compare_hashes,
)

logger = logging.getLogger(__name__)


def get_company_name(instance):
    # ManyToMany relationships can only exist if the instance is in the db. Those will have a pk.
    if instance.pk:
        return ", ".join(str(partner) for partner in instance.partners.all())
    else:
        return None


class UserProfile(models.Model):
    """
    This is for storing data that relates only to accounts on TWLight, _not_ to
    Wikipedia accounts. All TWLight users have user profiles.
    """

    class Meta:
        app_label = "users"
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"

    # Related name for backwards queries defaults to "userprofile".
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Have they agreed to our terms?
    terms_of_use = models.BooleanField(
        default=False, help_text="Has this user agreed with the terms of use?"
    )
    terms_of_use_date = models.DateField(
        blank=True,
        null=True,
        help_text="The date this user agreed to the terms of use.",
    )
    use_wp_email = models.BooleanField(
        default=True,
        help_text="Should we "
        "automatically update their email from their Wikipedia email when they "
        "log in? Defaults to True.",
    )
    lang = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        choices=settings.LANGUAGES,
        help_text="Language",
    )
    my_library_cache_key = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        editable=False,
    )
    send_renewal_notices = models.BooleanField(
        default=True, help_text="Does this user want renewal reminder notices?"
    )
    pending_app_reminders = models.BooleanField(
        default=True,
        help_text="Does this coordinator want pending app reminder notices?",
    )
    discussion_app_reminders = models.BooleanField(
        default=True,
        help_text="Does this coordinator want under discussion app reminder notices?",
    )
    approved_app_reminders = models.BooleanField(
        default=True,
        help_text="Does this coordinator want approved app reminder notices?",
    )
    # Temporary field to track sending of project page 2021 email to prevent duplication in case of error.
    project_page_2021_notification_sent = models.BooleanField(default=False)

    favorites = models.ManyToManyField(
        Partner,
        blank=True,
        help_text="The partner(s) that the user has marked as favorite.",
    )

    def delete_my_library_cache(self):
        """
        This method is for the convenience of skipping the import of django cache in each place that needs to invalidate the my_library cache
        """
        return cache.delete(self.my_library_cache_key)


def favorites_field_changed(sender, **kwargs):
    """
    This method validates whether a user has access to a partner they want to
    add to their favorites
    Added this signal per https://stackoverflow.com/a/56368721/4612594
    """
    instance = kwargs["instance"]
    authorized_partners = []
    authorizations = instance.user.authorizations.all()
    for authorization in authorizations:
        for partner in authorization.partners.all():
            authorized_partners.append(partner.pk)

    for favorite in instance.favorites.all():
        if favorite.pk not in authorized_partners:
            raise ValidationError(
                "We cannot add partner {partner} to your favorites because you don't have access to it".format(
                    partner=favorite.company_name
                )
            )


# This connects the UserProfile.favorites field to a signal to validate the
# partners being added
m2m_changed.connect(favorites_field_changed, sender=UserProfile.favorites.through)


class Editor(models.Model):
    """
    This model is for storing data related to people's accounts on Wikipedia.
    It is possible for users to have TWLight accounts and not have associated
    editors (if the account was created via manage.py createsuperuser),
    although some site functions will not be accessible.
    """

    class Meta:
        app_label = "users"
        verbose_name = "wikipedia editor"
        verbose_name_plural = "wikipedia editors"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Internal data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    # Database recordkeeping.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Set as non-editable.
    date_created = models.DateField(
        default=timezone.now,
        editable=False,
        help_text="When this profile was first created",
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~ Data from Wikimedia OAuth ~~~~~~~~~~~~~~~~~~~~~~~#
    # Uses same field names as OAuth, but with wp_ prefixed.
    # Data are current *as of the time of last TWLight login* but may get out of
    # sync thereafter.
    wp_username = models.CharField(max_length=235, help_text="Username")
    wp_registered = models.DateField(
        help_text="Date registered at Wikipedia", blank=True, null=True
    )
    wp_sub = models.IntegerField(
        unique=True, help_text="Wikipedia user ID"
    )  # WP user id.

    # Should we want to filter these to check for specific group membership or
    # user rights in future:
    # Editor.objects.filter(wp_groups__icontains=groupname) or similar.
    wp_groups = models.TextField(help_text="Wikipedia groups", blank=True)
    wp_rights = models.TextField(help_text="Wikipedia user rights", blank=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~ Non-editable data computed from Wikimedia OAuth / API Query ~~~~~~~~~~~~~~~~~~~~~~~#
    wp_valid = models.BooleanField(
        default=False,
        editable=False,
        help_text="At their last login, did this user meet the criteria in "
        "the terms of use?",
    )
    wp_account_old_enough = models.BooleanField(
        default=False,
        editable=False,
        help_text="At their last login, did this user meet the account age criterion in "
        "the terms of use?",
    )
    wp_enough_edits = models.BooleanField(
        default=False,
        editable=False,
        help_text="At their last login, did this user meet the total editcount criterion in "
        "the terms of use?",
    )
    wp_not_blocked = models.BooleanField(
        default=False,
        editable=False,
        help_text="At their last login, did this user meet the 'not currently blocked' criterion in "
        "the terms of use?",
    )
    wp_enough_recent_edits = models.BooleanField(
        default=False,
        editable=False,
        help_text="At their last login, did this user meet the recent editcount criterion in "
        "the terms of use?",
    )
    wp_bundle_eligible = models.BooleanField(
        default=False,
        editable=False,
        help_text="At their last login, did this user meet the criteria for access to the library card bundle?",
    )

    wp_block_hash = models.CharField(
        max_length=255,
        default="",
        blank=True,
        editable=False,
        help_text="A hash that is generated with a user's block data",
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ Staff-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ignore_wp_blocks = models.BooleanField(
        default=False,
        help_text="Ignore the 'not currently blocked' criterion for access?",
    )
    ignore_wp_bundle_eligible = models.BooleanField(
        default=False,
        help_text="Ignore all criteria for bundle access?",
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ User-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    contributions = models.TextField(
        help_text="Wiki contributions, as entered by user", blank=True
    )

    # Fields we may, or may not, have collected in the course of applications
    # for resource grants.
    # **** SENSITIVE USER DATA AHOY. ****
    real_name = models.CharField(max_length=128, blank=True)
    country_of_residence = models.CharField(max_length=128, blank=True)
    occupation = models.CharField(max_length=128, blank=True)
    affiliation = models.CharField(max_length=128, blank=True)

    def encode_wp_username(self, username):
        result = urllib.parse.quote(username)
        return result

    @property
    def wp_editcount(self):
        """
        Fetches latest editcount from EditorLogs related to this editor.
        Returns
        -------
        int : Most recently recorded Wikipedia editcount
        """
        try:
            return (EditorLog.objects.filter(editor=self).latest("timestamp")).editcount
        except models.ObjectDoesNotExist:
            pass

    @property
    def wp_editcount_updated(self):
        """
        Fetches timestamp of latest editcount from EditorLogs related to this editor.
        Returns
        -------
        datetime.datetime : datetime that editcount was recorded
        """
        try:
            return (EditorLog.objects.filter(editor=self).latest("timestamp")).timestamp
        except models.ObjectDoesNotExist:
            pass

    def wp_editcount_prev(
        self,
        current_datetime: timezone = None,
    ):
        """
        Fetches 30-day old editcount from EditorLogs related to this editor.
        Parameters
        ----------
        current_datetime : timezone
            optional timezone-aware timestamp override that represents now()

        Returns
        -------
        int : 30-day old Wikipedia editcount, if available.
        """
        if not current_datetime:
            current_datetime = timezone.now()
        try:
            return (
                EditorLog.objects.filter(
                    editor=self, timestamp__lte=current_datetime - timedelta(days=30)
                ).latest("timestamp")
            ).editcount
        except models.ObjectDoesNotExist:
            pass

    def wp_editcount_prev_updated(
        self,
        current_datetime: timezone = None,
    ):
        """
        Fetches timestamp of 30-day old editcount from EditorLogs related to this editor.
        Parameters
        ----------
        current_datetime : timezone
            optional timezone-aware timestamp override that represents now()

        Returns
        -------
        datetime.datetime : datetime that editcount_prev was recorded
        """
        if not current_datetime:
            current_datetime = timezone.now()
        try:
            return (
                EditorLog.objects.filter(
                    editor=self, timestamp__lte=current_datetime - timedelta(days=30)
                ).latest("timestamp")
            ).timestamp
        except models.ObjectDoesNotExist:
            pass

    def wp_editcount_recent(
        self,
        current_datetime: timezone = None,
    ):
        """
        Calculates recent editcount based on EditorLogs related to this editor.
        Used to determine if the editor meets the recent editcount criterion for access to the library card bundle.
        Parameters
        ----------
        current_datetime : timezone
            optional timezone-aware timestamp override that represents now()

        Returns
        -------
        int : number of recent Wikipedia edits, if available.
        """
        if not current_datetime:
            current_datetime = timezone.now()

        wp_editcount_prev = self.wp_editcount_prev(current_datetime=current_datetime)
        wp_editcount = self.wp_editcount

        if wp_editcount and wp_editcount_prev:
            recent_editcount = self.wp_editcount - self.wp_editcount_prev(
                current_datetime=current_datetime
            )
            return recent_editcount

    def update_editcount(
        self,
        editcount: int,
        current_datetime: timezone = None,
    ):
        """
        Logs current global_userinfo editcount and calculates recent edits against stored editor data.
        Parameters
        ----------
        editcount : int
            editcount provided by globaluserinfo or oauth.
        current_datetime : timezone
            optional timezone-aware timestamp override that represents now()

        Returns
        -------
        None
        """
        if not current_datetime:
            current_datetime = timezone.now()

        if not self.pk:
            self.save()

        editor_log_entry = EditorLog()
        editor_log_entry.editor = self
        editor_log_entry.editcount = editcount
        editor_log_entry.timestamp = current_datetime
        editor_log_entry.save()

        # Get the current recent editcount
        wp_editcount_recent = self.wp_editcount_recent(
            current_datetime=current_datetime
        )

        # A recent editcount of 10 is enough.
        if wp_editcount_recent is not None and wp_editcount_recent >= 10:
            self.wp_enough_recent_edits = True
        # Less than 10 is not enough.
        elif wp_editcount_recent is not None:
            self.wp_enough_recent_edits = False
        # If we don't have a recent editcount yet, consider it good enough.
        else:
            self.wp_enough_recent_edits = True

    def prune_editcount(
        self, current_datetime: timezone = None, daily_prune_range: int = 30
    ):
        """
        Removes extraneous and outdated EditorLogs related to this editor.
        Parameters
        ----------
        current_datetime : timezone
            optional timezone-aware timestamp override that represents now()
        daily_prune_range : int
            optional number of days to check for and prune excess daily counts. Defaults to 30.
        Returns
        -------
        None
        """
        if not current_datetime:
            current_datetime = timezone.now()

        # Prune EditorLogs that are more than 31 days old.
        EditorLog.objects.filter(
            editor=self, timestamp__lt=current_datetime - timedelta(days=31)
        ).delete()

        # Prune EditorLogs that:
        # have a timestamp between 12am `daily_prune_range` days ago and 12am yesterday
        # and are not the earliest EditorLog for that day.
        current_date = timezone.localtime(current_datetime).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for day in range(1, daily_prune_range):
            start_time = current_date - timedelta(days=day + 1)
            end_time = current_date - timedelta(days=day)
            extra_logs = EditorLog.objects.filter(
                editor=self, timestamp__gt=start_time, timestamp__lt=end_time
            )
            if extra_logs.count() > 1:
                try:
                    earliest = extra_logs.earliest("timestamp")
                    extra_logs = extra_logs.exclude(pk=earliest.pk)
                    extra_logs.delete()
                except models.ObjectDoesNotExist:
                    pass

    @cached_property
    def wp_user_page_url(self):
        encoded_username = self.encode_wp_username(self.wp_username)
        url = "{base_url}/User:{username}".format(
            base_url=settings.TWLIGHT_OAUTH_PROVIDER_URL, username=encoded_username
        )
        return url

    @cached_property
    def wp_talk_page_url(self):
        encoded_username = self.encode_wp_username(self.wp_username)
        url = "{base_url}/User_talk:{username}".format(
            base_url=settings.TWLIGHT_OAUTH_PROVIDER_URL, username=encoded_username
        )
        return url

    @cached_property
    def wp_email_page_url(self):
        encoded_username = self.encode_wp_username(self.wp_username)
        url = "{base_url}/Special:EmailUser/{username}".format(
            base_url=settings.TWLIGHT_OAUTH_PROVIDER_URL, username=encoded_username
        )
        return url

    @cached_property
    def wp_link_guc(self):
        encoded_username = self.encode_wp_username(self.wp_username)
        url = "{base_url}?user={username}".format(
            base_url="https://tools.wmflabs.org/guc/", username=encoded_username
        )
        return url

    @cached_property
    def wp_link_central_auth(self):
        encoded_username = self.encode_wp_username(self.wp_username)
        url = "{base_url}&target={username}".format(
            base_url="https://meta.wikimedia.org/w/index.php?title=Special%3ACentralAuth",
            username=encoded_username,
        )
        return url

    @property
    def get_wp_rights_display(self):
        """
        This should be used to display wp_rights in a template, or any time
        we need to manipulate the rights as a list rather than a string.
        Doesn't exist for batch loaded users.
        """
        if self.wp_groups:
            return json.loads(self.wp_rights)
        else:
            return None

    @property
    def get_wp_groups_display(self):
        """
        As above, but for groups.
        """
        if self.wp_groups:
            return json.loads(self.wp_groups)
        else:
            return None

    @property
    def wp_bundle_authorized(self):
        user_authorization = self.get_bundle_authorization
        # If the user has no Bundle authorization, they're not authorized
        if not user_authorization:
            return False
        else:
            # If the user has a Bundle authorization, ensure its validity
            return self.get_bundle_authorization.is_valid

    def get_global_userinfo(self, identity):
        self.check_sub(identity["sub"])
        return editor_global_userinfo(identity["sub"])

    def check_sub(self, wp_sub):
        """
        Verifies that the supplied Global Wikipedia User ID matches stored editor ID.
        Parameters
        ----------
        wp_sub : int
            Global Wikipedia User ID, used for guiid parameter in globaluserinfo calls.

        Returns
        -------
        None
        """

        if self.wp_sub != wp_sub:
            raise SuspiciousOperation(
                "Was asked to update Editor data, but the "
                "WP sub in the identity passed in did not match the wp_sub on "
                "the instance. Not updating."
            )

    @property
    def get_bundle_authorization(self):
        """
        Find this user's Bundle authorization. If they
        don't have one, return None.
        """
        # Although we have multiple partners with the BUNDLE authorization
        # method, we should only ever find one or zero authorizations
        # for bundle partners.
        try:
            return get_object_or_None(
                Authorization.objects.filter(
                    user=self.user, partners__authorization_method=Partner.BUNDLE
                ).distinct()  # distinct() required because partners__authorization_method is ManyToMany
            )
        # There should only be one bundle auth per user. Log an exception if there are duplicates
        except MultipleObjectsReturned:
            logger.exception(
                "{wp_username} has multiple bundle auths".format(
                    wp_username=self.wp_username
                )
            )
            # Grab the first auth after logging in the case of duplicates so the user may continue as normal
            return (
                Authorization.objects.filter(
                    user=self.user, partners__authorization_method=Partner.BUNDLE
                )
                .distinct()
                .first()
            )

    def update_bundle_authorization(self):
        """
        Create or expire this user's bundle authorizations
        if necessary.
        The list of partners for the auth will be kept up-to-date
        elsewhere after initial creation, so no need to worry about
        updating an existing auth with the latest bundle partner
        changes here.
        """
        user_authorization = self.get_bundle_authorization
        if not user_authorization:
            # If the user has become eligible, we should create an auth
            if self.wp_bundle_eligible:
                twl_team = User.objects.get(username="TWL Team")
                bundle_partners = Partner.objects.filter(
                    authorization_method=Partner.BUNDLE
                )
                user_authorization = Authorization(user=self.user, authorizer=twl_team)
                user_authorization.save()

                for partner in bundle_partners:
                    user_authorization.partners.add(partner)
            return

        # If we got a bundle authorization, let's see if we need to modify it
        # If the user is no longer eligible, we should expire the auth
        if not self.wp_bundle_eligible:
            user_authorization.date_expires = date.today() - timedelta(days=1)
            user_authorization.save()
        else:
            # If the user is eligible, and has an expiry date on their
            # bundle authorization, that probably means we previously
            # expired it. So reset it to being active.
            # If they're eligible and have no expiry date, then we
            # don't need to do anything else, they remain authorized.
            if user_authorization.date_expires:
                user_authorization.date_expires = None
                user_authorization.save()

    def update_from_wikipedia(
        self,
        identity: dict,
        lang: str,
        global_userinfo: dict = None,
        current_datetime: timezone = None,
    ):
        """
        Given the dict returned from the Wikipedia OAuth /identify endpoint,
        update the instance accordingly.

        This assumes that we have used wp_sub to match the Editor and the
        Wikipedia info.

        Parameters
        ----------
        identity : dict
            {
                'username': identity['username'],       # wikipedia username
                'sub': identity['sub'],                 # wikipedia ID
                'rights': identity['rights'],           # user rights on-wiki
                'groups': identity['groups'],           # user groups on-wiki
                'editcount': identity['editcount'],
                'email': identity['email'],

                # Date registered: YYYYMMDDHHMMSS
                'registered': identity['registered']
            }

            We could attempt to harvest real name, but we won't; we'll let
            users enter it if required by partners, and avoid knowing the
            data otherwise.
        lang : str
        global_userinfo : dict
            Optional override currently used for tests only. Defaults to fetching from global_userinfo API.
            {
                "home": str,                            # SUL home wiki
                "id": int,                              # Same as identity['sub']
                "registration": datetime.datetime,      # Wikipedia account registration date.
                "name": str,                            # Same as identity['username']
                "editcount": int,                       # Same as identity['editcount']
                "merged": [                             # List of wiki accounts attached to the SUL account
                    {
                        "wiki": str,                        # Wiki name
                        "url": str,                         # Wiki URL
                        "timestamp": datetime.datetime,
                        "method": str,
                        "editcount": int,
                        "registration": datetime.datetime,  # Wiki registration date.
                        "groups": list,                     # user groups on-wiki.
                    },
                    ...
                ],
            }
        current_datetime : timezone
            optional timezone-aware timestamp override that represents now()
        Returns
        -------
        None
        """
        if not current_datetime:
            current_datetime = timezone.now()

        if global_userinfo:
            self.check_sub(global_userinfo["id"])
        else:
            global_userinfo = self.get_global_userinfo(identity)

        self.wp_username = identity["username"]
        self.wp_rights = json.dumps(identity["rights"])
        self.wp_groups = json.dumps(identity["groups"])
        if global_userinfo:
            blocked_dict = {}
            self.update_editcount(
                global_userinfo["editcount"], current_datetime=current_datetime
            )
            self.wp_not_blocked = editor_not_blocked(global_userinfo["merged"])
            previous_block_hash = self.wp_block_hash
            blocked_dict = editor_make_block_dict(global_userinfo["merged"])
            self.wp_block_hash = editor_compare_hashes(
                previous_block_hash,
                blocked_dict,
                self.wp_username,
                self.ignore_wp_blocks,
            )

        # if the account is already old enough, we shouldn't run this check everytime
        # since this flag should never return back to False
        if self.wp_registered is None or not self.wp_account_old_enough:
            self.wp_registered = editor_reg_date(identity, global_userinfo)
            self.wp_account_old_enough = editor_account_old_enough(self.wp_registered)

        self.wp_enough_edits = editor_enough_edits(self.wp_editcount)
        self.wp_valid = editor_valid(
            self.wp_enough_edits,
            self.wp_account_old_enough,
            self.wp_not_blocked,
            self.ignore_wp_blocks,
        )

        self.wp_bundle_eligible = editor_bundle_eligible(self)

        self.save()

        self.update_bundle_authorization()

        # This will be True the first time the user logs in, since use_wp_email
        # defaults to True. Therefore we will initialize the email field if
        # they have an email at WP for us to initialize it with.
        if self.user.userprofile.use_wp_email:
            try:
                self.user.email = identity["email"]
            except KeyError:
                # Email isn't guaranteed to be present in identity - don't do
                # anything if we can't find it.
                logger.exception("Unable to get Editor email address from Wikipedia.")

        self.user.save()

        # Add language if the user hasn't selected one
        if not self.user.userprofile.lang:
            self.user.userprofile.lang = lang
            self.user.userprofile.save()

    def __str__(self):
        # Translators: Do not translate.
        return _("{wp_username}").format(wp_username=self.wp_username)

    def get_absolute_url(self):
        return reverse("users:editor_detail", kwargs={"pk": self.pk})


class EditorLog(models.Model):
    """"""

    class Meta:
        app_label: "users"
        verbose_name: "editorlog"
        verbose_name_plural: "editorlogs"
        get_latest_by: "timestamp"

    editor = models.ForeignKey(
        Editor, related_name="editorlogs", on_delete=models.CASCADE, db_index=True
    )

    editcount = models.IntegerField(
        default=None,
        null=False,
        blank=False,
        editable=False,
        help_text="Wikipedia edit count",
    )

    timestamp = models.DateTimeField(
        default=None,
        null=False,
        blank=False,
        editable=False,
        db_index=True,
        help_text="When the editcount was updated from Wikipedia",
    )


class Authorization(models.Model):
    """
    Authorizations track editor access to partner resources. The approval or
    sending of an application triggers the creation of an authorization for the
    relevant editor to access the approved resource. Authorizations may be
    created manually for testing.
    """

    class Meta:
        app_label = "users"
        verbose_name = "authorization"
        verbose_name_plural = "authorizations"

    coordinators = get_coordinators()

    # Users may have multiple authorizations.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        related_name="authorizations",
        help_text="The authorized user.",
    )

    # Authorizers may authorize many users.
    authorizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The authorizing user.",
    )

    date_authorized = models.DateField(auto_now_add=True)

    date_expires = models.DateField(
        blank=True, null=True, help_text="The date this authorization expires."
    )

    partners = models.ManyToManyField(
        Partner,
        blank=True,
        # Limit to available partners.
        limit_choices_to=(models.Q(status__in=[Partner.AVAILABLE, Partner.WAITLIST])),
        help_text="The partner(s) for which the editor is authorized.",
    )

    reminder_email_sent = models.BooleanField(
        default=False,
        help_text="Have we sent a reminder email about this authorization?",
    )

    @property
    def is_valid(self):
        """
        Gives Boolean response regarding the current validity of this authorization.
        """
        # We assume the authorization is invalid unless we know better.
        valid = False
        today = datetime.today().date()
        # When updating this logic, please also update the filter in
        # TWLight.applications.helpers.get_active_authorizations function,
        # so that they remain in sync and return the same type of authorizations.
        if (
            # Valid authorizations always have an authorizer, and user and a partner_id.
            self.authorizer
            and self.user
            and self.partners.all().exists()
            # and a valid authorization date that is now or in the past
            and self.date_authorized
            and self.date_authorized <= today
            # and an expiration date in the future (or no expiration date).
            and (
                (self.date_expires and self.date_expires >= today)
                or not self.date_expires
            )
        ):
            valid = True
        return valid

    # Try to return a useful object name, if fields were set appropriately.
    def __str__(self):
        company_name = get_company_name(self)

        # In reality, we should always have an authorized user.
        if self.user:
            try:
                authorized_user = self.user.editor.wp_username
            except Editor.DoesNotExist:
                try:
                    authorized_user = self.user.username
                except User.DoesNotExist:
                    authorized_user = self.user
        else:
            authorized_user = None

        # In reality, we should always have an authorizer,
        # but we need to enhance the sample data commands so they don't
        # break the admin site in dev.
        if self.authorizer:
            try:
                authorizer = self.authorizer.editor.wp_username
            except Editor.DoesNotExist:
                try:
                    authorizer = self.authorizer.username
                except User.DoesNotExist:
                    authorizer = self.authorizer
        else:
            authorizer = None

        return "authorized: {authorized_user} - authorizer: {authorizer} - date_authorized: {date_authorized} - " "company_name: {company_name}".format(
            authorized_user=authorized_user,
            authorizer=authorizer,
            date_authorized=self.date_authorized,
            company_name=company_name,
        )

    def get_latest_app(self):
        """
        Returns the latest app corresponding to this auth in which the the status is *NOT* NOT_APPROVED.
        """
        from TWLight.applications.models import Application

        if self.partners.all().count() == 1 and self.user and self.user.editor:
            partner = self.partners.all()
            try:
                return Application.objects.filter(
                    ~Q(status=Application.NOT_APPROVED),
                    partner__in=partner,
                    editor=self.user.editor,
                ).latest("id")
            except Application.DoesNotExist:
                return None

    def get_open_app(self):
        """
        Returns an open app corresponding to this auth.
        Open apps have a status of PENDING, QUESTION, or APPROVED.
        """
        from TWLight.applications.models import Application

        if self.partners.all().count() == 1 and self.user and self.user.editor:
            try:
                return Application.objects.filter(
                    editor=self.user.editor,
                    status__in=(
                        Application.PENDING,
                        Application.QUESTION,
                        Application.APPROVED,
                    ),
                    partner__in=self.partners.all(),
                ).latest("date_created")
            except Application.DoesNotExist:
                return None

    def get_latest_sent_app(self):
        """
        Returns the latest app corresponding to this auth in which the the status is SENT.
        """
        from TWLight.applications.models import Application

        if self.partners.all().count() == 1 and self.user and self.user.editor:
            try:
                return Application.objects.filter(
                    status=Application.SENT,
                    partner__in=self.partners.all(),
                    editor=self.user.editor,
                ).latest("id")
            except Application.DoesNotExist:
                return None

    @property
    def about_to_expire(self):
        # less than 30 days but greater than -1 day is when we consider an authorization about to expire
        today = date.today()
        if (
            self.date_expires
            and self.date_expires - today < timedelta(days=30)
            and not self.date_expires < today
        ):
            return True
        else:
            return False

    def get_authorization_method(self):
        """
        For this authorization, returns the linked authorization
        method of the partner, as applicable
        """
        if self.pk and self.partners.exists():
            # Even if there is more than one partner, there should only be one authorization_method.
            authorization_method = (
                self.partners.all()
                .values_list("authorization_method", flat=True)
                .distinct()
                .get()
            )
        else:
            authorization_method = None

        return authorization_method

    @property
    def is_bundle(self):
        """
        Returns True if this authorization is to a Bundle partner
        and False otherwise.
        """
        authorization_method = self.get_authorization_method()

        if authorization_method == Partner.BUNDLE:
            return True
        else:
            return False

    def is_accessed_via_proxy(self):
        """
        Do users access the collection for this authorization via the proxy, or not?
        Returns True if the partner has an authorization_method of Proxy or Bundle.
        """
        authorization_method = self.get_authorization_method()

        if authorization_method in [Partner.PROXY, Partner.BUNDLE]:
            return True
        else:
            return False

    def clean(self):
        """
        Run custom validations for Authorization objects, both when the
        object is created and updated, separately
        """
        # Run custom validation for ManyToMany Partner relationship.
        # This only works on updates to existing instances because ManyToMany relationships only exist
        # if the instance is in the db. Those will have a pk.
        # The admin form calls validate_partners before saving, so we are covered between the two.
        if self.pk:
            validate_partners(self.partners)

        # If the Authorization *is* being created, then we want to validate
        # that the authorizer field is a user in expected groups.
        # A user can stop being in one of these groups later, so we
        # only verify this on object creation.
        else:
            validate_authorizer(self.authorizer)
