"""
This file holds user profile information. (The base User model is part of
Django; profiles extend that with locally useful information.)

TWLight has three user classes:
* editors
* coordinators
* site administrators.

_Editors_ are Wikipedia editors who are applying for TWL resource access
grants. We track some of their data here to facilitate access grant
decisions.

_Coordinators_ are the Wikipedians who have responsibility for evaluating
and deciding on access grants. Site administrators should designate
coordinators through the Django admin site. Right now the only thing we
need to track about coordinators is the fact that they ARE coordinators,
but a class is provided in anticipation of future need.

_Site administrators_ have admin privileges for this site. They have no special
handling in this file; they are handled through the native Django is_admin
flag, and site administrators have responsibility for designating who has that
flag through the admin interface.

We don't actually need to track editor data for coordinators or site admins,
although in practice we probably will, if they create accounts through the
public signup process.

This file is for defining information we need to track about each user class.
The groups themselves are defined in groups.py.

New users who sign up via oauth will be created as editors. Site administrators
must define coordinators manually in the Django admin site, by adding them to
the coordinators group.
"""

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import ugettext as _

from .helpers.wiki_list import WIKIS

class Editor(models.Model):
    # Internal data
    user = models.OneToOneField(User)
    last_updated = models.DateField(auto_now=True,
        help_text=_("When this information was last edited"))
    account_created = models.DateField(auto_now_add=True,
        help_text=_("When this information was first created"))

    # ~~~~~~~~~~~~~~~~~~~~~~~ Data from Wikimedia OAuth ~~~~~~~~~~~~~~~~~~~~~~~
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
    wp_groups = ArrayField(base_field=models.CharField(max_length=25),
        help_text=_("Wikipedia groups"))
    wp_rights = ArrayField(base_field=models.CharField(max_length=50),
        help_text=_("Wikipedia user rights"))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ User-entered data ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    home_wiki = models.CharField(max_length=20, choices=WIKIS,
        help_text=_("Home wiki, as indicated by user"))
    contributions = models.TextField(
        help_text=_("Wiki contributions, as entered by user"))
    email = models.EmailField(help_text=_("Email, as entered by user"))


    @property
    def wp_link_edit_count(self):
        url = '{base_url}?user={user.wp_username}&project={user.home_wiki}'.format(
            base_url='https://tools.wmflabs.org/xtools-ec/',
            user=self
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
        url = '{base_url}?user={user.username}&project={user.home_wiki}&namespace=all&redirects=none'.format(
            base_url='https://tools.wmflabs.org/xtools/pages/index.php',
            user=self
        )
        return url


class Coordinator(models.Model):
    user = models.OneToOneField(User)
    is_coordinator = models.BooleanField(default=False,
        help_text=_("Does this user have coordinator permissions for this site?"))
