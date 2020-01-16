# -*- coding: utf-8 -*-

"""
This file holds user profile information. (The base User model is part of
Django; profiles extend that with locally useful     information.)

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
accounts without attached Editors in the admin site, if for some reason it's
useful to have account holders without attached Wikipedia data.
"""
from datetime import datetime, date, timedelta
import json
import logging
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.timezone import now
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from TWLight.resources.models import Partner, Stream
from TWLight.users.groups import get_coordinators

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


# Create user profiles automatically when users are created.
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


models.signals.post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)


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
    # Data are current *as of the time of TWLight signup* but may get out of
    # sync thereafter.
    wp_username = models.CharField(max_length=235, help_text=_("Username"))
    # Translators: The total number of edits this user has made to all Wikipedia projects
    wp_editcount = models.IntegerField(
        help_text=_("Wikipedia edit count"), blank=True, null=True
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
    wp_valid = models.BooleanField(
        default=False,
        # Translators: Help text asking whether the user met the requirements for access (see https://wikipedialibrary.wmflabs.org/about/) the last time they logged in (when their information was last updated).
        help_text=_(
            "At their last login, did this user meet the criteria in "
            "the terms of use?"
        ),
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

    def _is_user_valid(self, identity, global_userinfo):
        """
        Check for the eligibility criteria laid out in the terms of service.
        To wit, users must:
        * Have >= 500 edits
        * Be active for >= 6 months
        * Not be blocked on any projects

        Note that we won't prohibit signups or applications on this basis.
        Coordinators have discretion to approve people who are near the cutoff.
        """
        # If, for some reason, this information hasn't come through,
        # default to user not being valid.
        if not global_userinfo:
            return False
        # Check: >= 500 edits
        enough_edits = int(global_userinfo["editcount"]) >= 500

        # Check: registered >= 6 months ago
        # Try oauth registration date first. If it's not valid,
        # try the global_userinfo date
        try:
            reg_date = datetime.strptime(identity["registered"], "%Y%m%d%H%M%S").date()
        except:
            reg_date = datetime.strptime(
                global_userinfo["registration"], "%Y-%m-%dT%H:%M:%SZ"
            ).date()
        account_old_enough = datetime.today().date() - timedelta(days=182) >= reg_date

        # Check: not blocked
        not_blocked = identity["blocked"] == False

        if enough_edits and account_old_enough and not_blocked:
            return True
        else:
            logger.info(
                "Editor {username} was not valid.".format(username=self.wp_username)
            )
            return False

    def get_global_userinfo(self, identity):
        """
        Grab global user information from the API, which we'll use to overlay
        somme local wiki user info returned by OAuth.  Returns a dict like:

        global_userinfo:
          home:         "zhwikisource"
          id:           27666025
          registration: "2013-05-05T16:00:09Z"
          name:         "Example"
          editcount:    10
        """
        try:
            endpoint = "{base}/w/api.php?action=query&meta=globaluserinfo&guiuser={username}&guiprop=editcount&format=json&formatversion=2".format(
                base=identity["iss"], username=urllib.parse.quote(identity["username"])
            )

            results = json.loads(urllib.request.urlopen(endpoint).read())
            global_userinfo = results["query"]["globaluserinfo"]

            try:
                assert "missing" not in global_userinfo
                logger.info("Fetched global_userinfo for User.")
                return global_userinfo
            except AssertionError:
                logger.exception("Could not fetch global_userinfo for User.")
                return None
                pass

        except:
            logger.exception("Could not fetch global_userinfo for User.")
            return None
            pass

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
            self.wp_editcount = global_userinfo["editcount"]
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
                pass

        self.wp_registered = reg_date
        self.wp_valid = self._is_user_valid(identity, global_userinfo)
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
                pass

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
        unique_together = ("user", "partner", "stream")

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

    partner = models.ForeignKey(
        Partner,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
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
            and self.partner_id
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

        if self.partner:
            company_name = self.partner.company_name
        else:
            stream_name = None

        # In reality, we should always have an authorized user.
        if self.user:
            try:
                authorized_user = self.user.editor.wp_username
            except:
                try:
                    authorized_user = self.user.username
                except:
                    authorized_user = self.user
        else:
            authorized_user = None

        # In reality, we should always have an authorizer,
        # but we need to enhance the sample data commands so they don't
        # break the admin site in dev.
        if self.authorizer:
            try:
                authorizer = self.authorizer.editor.wp_username
            except:
                try:
                    authorizer = self.authorizer.username
                except:
                    authorizer = self.authorizer
        else:
            authorizer = None

        return "authorized: {authorized_user} - authorizer: {authorizer} - date_authorized: {date_authorized} - company_name: {company_name} - stream_name: {stream_name}".format(
            authorized_user=authorized_user,
            authorizer=authorizer,
            date_authorized=self.date_authorized,
            company_name=company_name,
            stream_name=stream_name,
        )

    def get_latest_app(self):
        from TWLight.applications.models import Application

        try:
            return Application.objects.filter(
                partner=self.partner, editor=self.user.editor
            ).latest("id")
        except Application.DoesNotExist:
            return None

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

    def is_renewable(self):
        partner = self.partner
        if (
            # We consider an authorization renewable, if the partner is PROXY and
            # about to expire or has already expired (is_valid returns false on expiry)
            # or if the partner isn't PROXY or BUNDLE, in which case the authorization
            # would have an empty date_expires field. The first would check still cover for
            # non-PROXY and non-BUNDLE partners with expiry dates.
            self.about_to_expire()
            or not self.is_valid
            or not partner.authorization_method == partner.PROXY
            and not partner.authorization_method == partner.BUNDLE
        ):
            return True
        else:
            return False


class ProxyAuthorization(Authorization):
    """
    This is only here so we can group authorizations with other auth-related things in admin.
    """

    class Meta:
        proxy = True
        app_label = "auth"
        # set following lines to display ProxyAuthorization as Authorization
        verbose_name = Authorization._meta.verbose_name
        verbose_name_plural = Authorization._meta.verbose_name_plural
