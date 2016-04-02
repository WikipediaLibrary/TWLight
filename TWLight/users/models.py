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
import json

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from .helpers.wiki_list import WIKIS

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

    # Fields we may, or may not, have collected in the course of applications
    # for resource grants.
    # **** SENSITIVE USER DATA AHOY. ****
    real_name = models.CharField(max_length=128, blank=True)
    country_of_residence = models.CharField(max_length=128, blank=True)
    occupation = models.CharField(max_length=128, blank=True)
    affiliation = models.CharField(max_length=128, blank=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~ Data from Wikimedia OAuth ~~~~~~~~~~~~~~~~~~~~~~~#
    # Uses same field names as OAuth, but with wp_ prefixed.
    # Data are current *as of the time of TWLight signup* but may get out of
    # sync thereafter.
    wp_username = models.CharField(max_length=235,
        help_text=_("Wikipedia username"))
    wp_editcount = models.IntegerField(help_text=_("Wikipedia edit count"))
    wp_registered = models.DateField(help_text=_("Date registered at Wikipedia"))
    # TODO what is the actual data format?
    wp_sub = models.IntegerField(help_text=_("Wikipedia user ID")) # WP user id.

    # ArrayField is a postgres-specific field type for storing
    # lists in a structured format. ArrayField will permit us
    # to do queries of the sort "filter all editors belonging
    # to group X", which should suffice for our purposes. Creating
    # actual db representations of each group and right so as to
    # create FKs to all the users possessing them seems like overkill.
    #wp_groups = ArrayField(base_field=models.CharField(max_length=25),
    #    help_text=_("Wikipedia groups"))
    #wp_rights = ArrayField(base_field=models.CharField(max_length=50),
    #    help_text=_("Wikipedia user rights"))

    _wp_internal = models.TextField()

    # this does not actually work because json.dumps doesn't perform enough
    # validation - it can dump things we cannot subsequently load. It may be
    # that all we need is to store a string and use
    # filter(wp_groups__icontains=groupname) and call that good enough.
    @property
    def wp_internal(self):
        return json.loads(self._wp_internal)
    @wp_internal.setter
    def wp_internal(self, value):
        self._wp_internal = json.dumps(value)
    

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ User-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    home_wiki = models.CharField(max_length=4, choices=WIKIS,
        help_text=_("Home wiki, as indicated by user"))
    contributions = models.TextField(
        help_text=_("Wiki contributions, as entered by user"))
    email = models.EmailField(help_text=_("Email, as entered by user"))


    @property
    def wp_user_page_url(self):
        url = 'https://{home_wiki_link}/wiki/User:{user.wp_username}'.format(
            home_wiki_link=self.get_home_wiki_display(), user=self)
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


    def __str__(self):
        return self.wp_username

