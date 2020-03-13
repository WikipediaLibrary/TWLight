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
import urllib.request, urllib.parse, urllib.error

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from TWLight.resources.models import Partner, Stream
from TWLight.users.groups import get_coordinators

from TWLight.users.helpers.editor_data import (
    editor_global_userinfo,
    editor_valid,
    editor_account_old_enough,
    editor_enough_edits,
    editor_not_blocked,
    editor_reg_date,
    editor_recent_edits,
    editor_bundle_eligible,
)

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    """
    This is for storing data that relates only to accounts on TWLight, _not_ to
    Wikipedia accounts. All TWLight users have user profiles.
    """

    class Meta:
        app_label = "users"
        # Translators: Gender unknown. This will probably only be displayed on admin-only pages.
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"

    # Related name for backwards queries defaults to "userprofile".
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    # Have they agreed to our terms?
    terms_of_use = models.BooleanField(
        default=False,
        # Translators: Users must agree to the website terms of use.
        help_text=_("Has this user agreed with the terms of use?"),
    )
    terms_of_use_date = models.DateField(
        blank=True,
        null=True,
        # Translators: This field records the date the user agreed to the website terms of use.
        help_text=_("The date this user agreed to the terms of use."),
    )
    # Translators: An option to set whether users email is copied to their website account from Wikipedia when logging in.
    use_wp_email = models.BooleanField(
        default=True,
        help_text=_(
            "Should we "
            "automatically update their email from their Wikipedia email when they "
            "log in? Defaults to True."
        ),
    )
    lang = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        choices=settings.LANGUAGES,
        # Translators: Users' detected or selected language.
        help_text=_("Language"),
    )
    send_renewal_notices = models.BooleanField(
        default=True,
        # Translators: Description of the option users have to enable or disable reminder emails for renewals
        help_text=_("Does this user want renewal reminder notices?"),
    )
    pending_app_reminders = models.BooleanField(
        default=True,
        # Translators: Description of the option coordinators have to enable or disable to receive (or not) reminder emails for pending applications
        help_text=_("Does this coordinator want pending app reminder notices?"),
    )
    discussion_app_reminders = models.BooleanField(
        default=True,
        # Translators: Description of the option coordinators have to enable or disable to receive (or not) reminder emails for under discussion applications
        help_text=_(
            "Does this coordinator want under discussion app reminder notices?"
        ),
    )
    approved_app_reminders = models.BooleanField(
        default=True,
        # Translators: Description of the option coordinators have to enable or disable to receive (or not) reminder emails for approved applications
        help_text=_("Does this coordinator want approved app reminder notices?"),
    )


class Editor(models.Model):
    """
    This model is for storing data related to people's accounts on Wikipedia.
    It is possible for users to have TWLight accounts and not have associated
    editors (if the account was created via manage.py createsuperuser),
    although some site functions will not be accessible.
    """

    class Meta:
        app_label = "users"
        # Translators: Gender unknown. This will probably only be displayed on admin-only pages.
        verbose_name = "wikipedia editor"
        verbose_name_plural = "wikipedia editors"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Internal data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    # Database recordkeeping.
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    # Set as non-editable.
    date_created = models.DateField(
        default=now,
        editable=False,
        # Translators: The date the user's profile was created on the website (not on Wikipedia).
        help_text=_("When this profile was first created"),
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~ Data from Wikimedia OAuth ~~~~~~~~~~~~~~~~~~~~~~~#
    # Uses same field names as OAuth, but with wp_ prefixed.
    # Data are current *as of the time of last TWLight login* but may get out of
    # sync thereafter.
    wp_username = models.CharField(max_length=235, help_text=_("Username"))
    # Translators: The total number of edits this user has made to all Wikipedia projects
    wp_editcount = models.IntegerField(
        help_text=_("Wikipedia edit count"), blank=True, null=True
    )
    wp_editcount_updated = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        editable=False,
        # Translators: Date and time that wp_editcount was updated from Wikipedia.
        help_text=_("When the editcount was updated from Wikipedia"),
    )
    # Translators: The date this user registered their Wikipedia account
    wp_registered = models.DateField(
        help_text=_("Date registered at Wikipedia"), blank=True, null=True
    )
    wp_sub = models.IntegerField(
        unique=True,
        # Translators: The User ID for this user on Wikipedia
        help_text=_("Wikipedia user ID"),
    )  # WP user id.

    # Should we want to filter these to check for specific group membership or
    # user rights in future:
    # Editor.objects.filter(wp_groups__icontains=groupname) or similar.
    # Translators: Lists the user groups (https://en.wikipedia.org/wiki/Wikipedia:User_access_levels) this editor has. e.g. Confirmed, Administrator, CheckUser
    wp_groups = models.TextField(help_text=_("Wikipedia groups"), blank=True)
    # Translators: Lists the individual user rights permissions the editor has on Wikipedia. e.g. sendemail, createpage, move
    wp_rights = models.TextField(help_text=_("Wikipedia user rights"), blank=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~ Non-editable data computed from Wikimedia OAuth / API Query ~~~~~~~~~~~~~~~~~~~~~~~#
    wp_valid = models.BooleanField(
        default=False,
        editable=False,
        # Translators: Help text asking whether the user met all requirements for access (see https://wikipedialibrary.wmflabs.org/about/) the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the criteria in "
            "the terms of use?"
        ),
    )
    wp_account_old_enough = models.BooleanField(
        default=False,
        editable=False,
        # Translators: Help text asking whether the user met the account age requirement for access (see https://wikipedialibrary.wmflabs.org/about/) the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the account age criterion in "
            "the terms of use?"
        ),
    )
    wp_enough_edits = models.BooleanField(
        default=False,
        editable=False,
        # Translators: Help text asking whether the user met the total editcount requirement for access (see https://wikipedialibrary.wmflabs.org/about/) the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the total editcount criterion in "
            "the terms of use?"
        ),
    )
    wp_not_blocked = models.BooleanField(
        default=False,
        editable=False,
        # Translators: Help text asking whether the user met the 'not currently blocked' requirement for access (see https://wikipedialibrary.wmflabs.org/about/) the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the 'not currently blocked' criterion in "
            "the terms of use?"
        ),
    )
    wp_enough_recent_edits = models.BooleanField(
        default=False,
        editable=False,
        # Translators: Help text asking whether the user met the recent editcount requirement for access to the library card bundle the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the recent editcount criterion in "
            "the terms of use?"
        ),
    )
    wp_editcount_prev_updated = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        editable=False,
        # Translators: The date and time that wp_editcount_prev was updated from Wikipedia.
        help_text=_("When the previous editcount was last updated from Wikipedia"),
    )
    # wp_editcount_prev is initially set to 0 so that all edits get counted as recent edits for new users.
    wp_editcount_prev = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        editable=False,
        # Translators: The number of edits this user made to all Wikipedia projects at a previous date.
        help_text=_("Previous Wikipedia edit count"),
    )

    # wp_editcount_recent is computed by selectively subtracting wp_editcount_prev from wp_editcount.
    wp_editcount_recent = models.IntegerField(
        default=0,
        null=True,
        blank=True,
        editable=False,
        # Translators: The number of edits this user recently made to all Wikipedia projects.
        help_text=_("Recent Wikipedia edit count"),
    )
    wp_bundle_eligible = models.BooleanField(
        default=False,
        editable=False,
        # Translators: Help text asking whether the user met all requirements for access to the library card bundle the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the criteria for access to the library card bundle?"
        ),
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ Staff-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ignore_wp_blocks = models.BooleanField(
        default=False,
        # Translators: Help text asking whether to ignore the 'not currently blocked' requirement for access.
        help_text=_("Ignore the 'not currently blocked' criterion for access?"),
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ User-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    contributions = models.TextField(
        # Translators: Describes information added by the user to describe their Wikipedia edits.
        help_text=_("Wiki contributions, as entered by user"),
        blank=True,
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

    def get_global_userinfo(self, identity):
        return editor_global_userinfo(identity["username"], identity["sub"], True)

    def update_from_wikipedia(self, identity, lang):
        """
        Given the dict returned from the Wikipedia OAuth /identify endpoint,
        update the instance accordingly.

        This assumes that we have used wp_sub to match the Editor and the
        Wikipedia info.

        Expected identity data:

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
        """

        try:
            assert self.wp_sub == identity["sub"]
        except AssertionError:
            logger.exception(
                "Was asked to update Editor data, but the "
                "WP sub in the identity passed in did not match the wp_sub on "
                "the instance. Not updating."
            )
            raise

        global_userinfo = self.get_global_userinfo(identity)

        self.wp_username = identity["username"]
        self.wp_rights = json.dumps(identity["rights"])
        self.wp_groups = json.dumps(identity["groups"])
        if global_userinfo:
            self.wp_editcount_prev_updated, self.wp_editcount_prev, self.wp_editcount_recent, self.wp_enough_recent_edits = editor_recent_edits(
                global_userinfo["editcount"],
                self.wp_editcount_updated,
                self.wp_editcount,
                self.wp_editcount_prev_updated,
                self.wp_editcount_prev,
                self.wp_editcount_recent,
                self.wp_enough_recent_edits,
            )
            self.wp_editcount = global_userinfo["editcount"]
            self.wp_not_blocked = editor_not_blocked(global_userinfo["merged"])
            self.wp_editcount_updated = now()

        self.wp_registered = editor_reg_date(identity, global_userinfo)
        self.wp_account_old_enough = editor_account_old_enough(self.wp_registered)
        self.wp_enough_edits = editor_enough_edits(self.wp_editcount)
        self.wp_valid = editor_valid(
            self.wp_enough_edits,
            self.wp_account_old_enough,
            self.wp_not_blocked,
            self.ignore_wp_blocks,
        )
        self.wp_bundle_eligible = editor_bundle_eligible(
            self.wp_valid, self.wp_enough_recent_edits
        )
        self.save()

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
        return _("{wp_username}").format(
            # Translators: Do not translate.
            wp_username=self.wp_username
        )

    def get_absolute_url(self):
        return reverse("users:editor_detail", kwargs={"pk": self.pk})


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
        # Translators: In the administrator interface, this text is help text for a field where staff can specify the username of the authorized editor.
        help_text=_("The authorized user."),
    )

    # Authorizers may authorize many users.
    authorizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        # Really this should be limited to superusers or the associated partner coordinator instead of any coordinator. This object structure needs to change a bit for that to be possible.
        limit_choices_to=(
            models.Q(is_superuser=True) | models.Q(groups__name="coordinators")
        ),
        # Translators: In the administrator interface, this text is help text for a field where staff can specify the user who authorized the editor.
        help_text=_("The authorizing user."),
    )

    date_authorized = models.DateField(auto_now_add=True)

    date_expires = models.DateField(
        blank=True,
        null=True,
        # Translators: This field records the date the authorization expires.
        help_text=_("The date this authorization expires."),
    )

    partners = models.ManyToManyField(
        Partner,
        blank=True,
        # Limit to available partners.
        limit_choices_to=(models.Q(status=0)),
        # Translators: In the administrator interface, this text is help text for a field where staff can specify the partner for which the editor is authorized.
        help_text=_("The partner for which the editor is authorized."),
    )

    stream = models.ForeignKey(
        Stream,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        # Limit to available partners.
        limit_choices_to=(models.Q(partner__status=0)),
        # Translators: In the administrator interface, this text is help text for a field where staff can specify the partner for which the editor is authoried.
        help_text=_("The stream for which the editor is authorized."),
    )

    reminder_email_sent = models.BooleanField(
        default=False,
        # Translators: In the administrator interface, this text is help text for a field which tracks whether a reminder has been sent about this authorization yet.
        help_text=_("Have we sent a reminder email about this authorization?"),
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
        if self.stream:
            stream_name = self.stream.name
        else:
            stream_name = None

        if self.partners.all().exists():
            company_name = "\n".join([p.company_name for p in self.partners.all()])
        else:
            company_name = None

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

        return (
            "authorized: {authorized_user} - authorizer: {authorizer} - date_authorized: {date_authorized} - "
            "company_name: {company_name} - stream_name: {stream_name}".format(
                authorized_user=authorized_user,
                authorizer=authorizer,
                date_authorized=self.date_authorized,
                company_name=company_name,
                stream_name=stream_name,
            )
        )

    def get_latest_app(self):
        """
        Returns the latest application for a corresponding authorization,
        except when the status of the application is NOT_APPROVED, in which
        case returns the previous not NOT_APPROVED application.
        """
        from TWLight.applications.models import Application

        try:
            if self.stream:
                return Application.objects.filter(
                    ~Q(status=Application.NOT_APPROVED),
                    specific_stream=self.stream,
                    editor=self.user.editor,
                ).latest("id")
            else:
                return Application.objects.filter(
                    ~Q(status=Application.NOT_APPROVED),
                    partner=self.partner,
                    editor=self.user.editor,
                ).latest("id")
        except Application.DoesNotExist:
            return None

    def get_latest_sent_app(self):
        from TWLight.applications.models import Application

        try:
            return Application.objects.filter(
                status=Application.SENT, partner=self.partner, editor=self.user.editor
            ).latest("id")
        except Application.DoesNotExist:
            return None

    def get_access_url(self):
        """
        For this authorization, which URL - if any - will users click to get to the collection?
        Returns a string if an access URL exists, and None if it doesn't.
        """
        if self.stream:
            access_url = self.stream.get_access_url
        else:
            access_url = self.partner.get_access_url

        return access_url

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
        method of the partner or stream, as applicable
        """
        if self.stream:
            authorization_method = self.stream.authorization_method
        else:
            authorization_method = self.partner.authorization_method

        return authorization_method

    def is_bundle(self):
        """
        Returns True if this authorization is to a Bundle partner
        or stream and False otherwise.
        """
        authorization_method = self.get_authorization_method()

        if authorization_method == Partner.BUNDLE:
            return True
        else:
            return False

    def is_accessed_via_proxy(self):
        """
        Do users access the collection for this authorization via the proxy, or not?
        Returns True if the partner or stream has an authorization_method of Proxy or Bundle.
        """
        authorization_method = self.get_authorization_method()

        if authorization_method in [Partner.PROXY, Partner.BUNDLE]:
            return True
        else:
            return False
