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
from datetime import datetime
import json
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext as _

from .helpers.wiki_list import WIKIS


logger = logging.getLogger(__name__)


class Editor(models.Model):
    class Meta:
        app_label = 'users'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Internal data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
    # Database recordkeeping.
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    last_updated = models.DateField(auto_now=True,
        help_text=_("When this information was last edited"))
    account_created = models.DateField(auto_now_add=True,
        help_text=_("When this information was first created"))

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


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ User-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    home_wiki = models.CharField(max_length=4, choices=WIKIS,
        help_text=_("Home wiki, as indicated by user"),
        blank=True)
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
    def get_wp_rights_as_list(self):
        return list(self.wp_groups)

    
    @property
    def get_wp_rights_as_list(self):
        return list(self.wp_rights)

    
    @property
    def wp_user_page_url(self):
        if self.get_home_wiki_display():
            url = 'https://{home_wiki_link}/wiki/User:{user.wp_username}'.format(
                home_wiki_link=self.get_home_wiki_display(), user=self)
        else:
            url = None
        return url


    @property
    def wp_link_edit_count(self):
        url = '{base_url}?user={user.wp_username}&project={home_wiki_link}'.format(
            base_url='https://tools.wmflabs.org/xtools-ec/',
            user=self,
            home_wiki_link=self.get_home_wiki_display()
        )
        return url


    @property
    def wp_link_sul_info(self):
        url = '{base_url}?username={user.username}'.format(
            base_url='https://tools.wmflabs.org/quentinv57-tools/tools/sulinfo.php',
            user=self
        )
        return url


    @property
    def wp_link_pages_created(self):
        url = '{base_url}?user={user.username}&project={home_wiki_link}&namespace=all&redirects=none'.format(
            base_url='https://tools.wmflabs.org/xtools/pages/index.php',
            user=self,
            home_wiki_link=self.get_home_wiki_display()
        )
        return url


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
        self.wp_rights = identity['rights']
        self.wp_groups = identity['groups']
        self.wp_editcount = identity['editcount']
        reg_date = datetime.strptime(identity['registered'], '%Y%m%d%H%M%S').date()
        self.wp_registered = reg_date
        self.save()

        self.user.email = identity['email']
        self.user.save()


    def __str__(self):
        return self.wp_username


    def get_absolute_url(self):
        return reverse('users:editor_detail', kwargs={'pk': self.user.pk})
