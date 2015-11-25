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
and deciding on access grants.

_Site administrators_ have admin privileges for this site. They have no special
handling in this file; they are handled through the native Django is_admin
flag, and site administrators have responsibility for designating who has that
flag through the admin interface.
"""

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models

from .helpers.wiki_list import WIKIS

class Editor(models.Model):
    # Internal data
    user = models.OneToOneField(User)
    last_updated = models.DateField(auto_now=True)

    # Data from Wikipedia
    wp_username = models.CharField(max_length=235)
    edit_count = models.IntegerField()
    registration_date = models.DateField()

    # ArrayField is a postgres-specific field type for storing
    # lists in a structured format. ArrayField will permit us
    # to do queries of the sort "filter all editors belonging
    # to group X", which should suffice for our purposes. Creating
    # actual db representations of each group and right so as to
    # create FKs to all the users possessing them seems like overkill.
    groups = ArrayField(base_field=models.CharField(max_length=25))
    userrights = ArrayField(base_field=models.CharField(max_length=50))

    # User-entered data
    home_wiki = models.CharField(max_length=20, CHOICES=WIKIS)
    contributions = models.TextField()
    email = models.EmailField()


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
