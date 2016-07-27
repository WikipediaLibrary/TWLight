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
accounts without attached Editors in the admin site, if for some reason it's
useful to have account holders without attached Wikipedia data.
"""
from datetime import datetime, timedelta
import json
import logging
import urllib2

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .helpers.wiki_list import WIKIS


logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    """
    This is for storing data that relates only to accounts on TWLight, _not_ to
    Wikipedia accounts. All TWLight users have user profiles.
    """
    class Meta:
        app_label = 'users'
        # Translators: Gender unknown. This will probably only be displayed on admin-only pages.
        verbose_name = 'user profile'
        verbose_name_plural = 'user profiles'

    # Related name for backwards queries defaults to "userprofile".
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    # Have they agreed to our terms?
    terms_of_use = models.BooleanField(default=False,
        help_text=_("Has this user agreed with the terms of use?"))


# Create user profiles automatically when users are created.
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

models.signals.post_save.connect(create_user_profile,
                                 sender=settings.AUTH_USER_MODEL)


class Editor(models.Model):
    """
    This model is for storing data related to people's accounts on Wikipedia.
    It is possible for users to have TWLight accounts and not have associated
    editors (if the account was created via manage.py createsuperuser),
    although some site functions will not be accessible.
    """
    class Meta:
        app_label = 'users'
        # Translators: Gender unknown. This will probably only be displayed on admin-only pages.
        verbose_name = 'wikipedia editor'
        verbose_name_plural = 'wikipedia editors'
        unique_together = ('wp_username', 'home_wiki')

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Internal data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    # Database recordkeeping.
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    last_updated = models.DateField(auto_now=True,
        help_text=_("When this information was last edited"))
    date_created = models.DateField(auto_now_add=True,
        help_text=_("When this profile was first created"))

    # ~~~~~~~~~~~~~~~~~~~~~~~ Data from Wikimedia OAuth ~~~~~~~~~~~~~~~~~~~~~~~#
    # Uses same field names as OAuth, but with wp_ prefixed.
    # Data are current *as of the time of TWLight signup* but may get out of
    # sync thereafter.
    wp_username = models.CharField(max_length=235,
        help_text=_("Wikipedia username"))
    wp_editcount = models.IntegerField(help_text=_("Wikipedia edit count"))
    wp_registered = models.DateField(help_text=_("Date registered at Wikipedia"))
    wp_sub = models.IntegerField(help_text=_("Wikipedia user ID")) # WP user id.

    # Should we want to filter these to check for specific group membership or
    # user rights in future:
    # Editor.objects.filter(wp_groups__icontains=groupname) or similar.
    wp_groups = models.TextField(help_text=_("Wikipedia groups"))
    wp_rights = models.TextField(help_text=_("Wikipedia user rights"))
    wp_valid = models.BooleanField(default=False,
        help_text=_('At their last login, did this '
        'user meet the criteria set forth in the Wikipedia Library Card '
        'Platform terms of use?'))


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ User-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    home_wiki = models.CharField(max_length=4, choices=WIKIS,
        help_text=_("Home wiki, as indicated by user"))
    contributions = models.TextField(
        help_text=_("Wiki contributions, as entered by user"),
        blank=True)

    # Fields we may, or may not, have collected in the course of applications
    # for resource grants.
    # **** SENSITIVE USER DATA AHOY. ****
    real_name = models.CharField(max_length=128, blank=True)
    country_of_residence = models.CharField(max_length=128, blank=True)
    occupation = models.CharField(max_length=128, blank=True)
    affiliation = models.CharField(max_length=128, blank=True)


    @property
    def wp_user_page_url(self):
        if self.get_home_wiki_display():
            url = 'https://{home_wiki_link}/wiki/User:{self.wp_username}'.format(
                home_wiki_link=self.get_home_wiki_display(), self=self)
        else:
            url = None
        return url


    @property
    def wp_link_edit_count(self):
        url = '{base_url}?user={self.wp_username}&project={home_wiki_link}'.format(
            base_url='https://tools.wmflabs.org/xtools-ec/',
            self=self,
            home_wiki_link=self.get_home_wiki_display()
        )
        return url


    @property
    def wp_link_sul_info(self):
        url = '{base_url}?username={self.wp_username}'.format(
            base_url='https://tools.wmflabs.org/quentinv57-tools/tools/sulinfo.php',
            self=self
        )
        return url


    @property
    def wp_link_pages_created(self):
        url = '{base_url}?user={self.wp_username}&project={home_wiki_link}&namespace=all&redirects=none'.format(
            base_url='https://tools.wmflabs.org/xtools/pages/index.php',
            self=self,
            home_wiki_link=self.get_home_wiki_display()
        )
        return url


    @property
    def get_wp_rights_display(self):
        """
        This should be used to display wp_rights in a template, or any time
        we need to manipulate the rights as a list rather than a string.
        """
        return json.loads(self.wp_rights)


    @property
    def get_wp_groups_display(self):
        """
        As above, but for groups.
        """
        return json.loads(self.wp_groups)


    def _is_user_valid(self, identity):
        """
        Check for the eligibility criteria laid out in the terms of service.
        To wit, users must:
        * Have >= 500 edits
        * Be active for >= 6 months
        * Have Special:Email User enabled
        * Not be blocked on any projects

        Note that we won't prohibit signups or applications on this basis.
        Coordinators have discretion to approve people who are near the cutoff.
        Furthermore, editors who are active on multiple wikis may meet this
        minimum when their account activity is aggregated even if they do not
        meet it on their home wiki - but we can only check the home wiki.
        """
        try:
            # Check: >= 500 edits
            assert int(identity['editcount']) >= 500

            # Check: registered >= 6 months ago
            reg_date = datetime.strptime(identity['registered'], '%Y%m%d%H%M%S').date()
            assert datetime.today().date() - timedelta(days=182) >= reg_date

            # Check: Special:Email User enabled
            endpoint = '{base}/w/api.php?action=query&format=json&meta=userinfo&uiprop=options'.format(base=identity['iss'])
            userinfo = json.loads(urllib2.urlopen(endpoint).read())
            logger.info('user info was {userinfo}'.format(userinfo=userinfo))

            disablemail = userinfo['query']['userinfo']['options']['disablemail']
            assert int(disablemail) == 0

            # Check: not blocked
            assert identity['blocked'] == False

            return True
        except AssertionError:
            logger.exception('User was not valid.')
            return False


    def update_from_wikipedia(self, identity):
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
            assert self.wp_sub == identity['sub']
        except AssertionError:
            logger.exception('Was asked to update Editor data, but the '
                'WP sub in the identity passed in did not match the wp_sub on '
                'the instance. Not updating.')
            raise

        self.wp_username = identity['username']
        self.wp_rights = json.dumps(identity['rights'])
        self.wp_groups = json.dumps(identity['groups'])
        self.wp_editcount = identity['editcount']
        reg_date = datetime.strptime(identity['registered'], '%Y%m%d%H%M%S').date()
        self.wp_registered = reg_date
        self.wp_valid = self._is_user_valid(identity)
        self.save()

        self.user.email = identity['email']

        self.user.save()


    def __str__(self):
        # Translators: This is how we display wikipedia editors' names by default. e.g. "ThatAndromeda (en.wikipedia.org)".
        return _('{wp_username} ({wiki})').format(
            wp_username=self.wp_username,
            wiki=self.get_home_wiki_display())


    def get_absolute_url(self):
        return reverse('users:editor_detail', kwargs={'pk': self.pk})
