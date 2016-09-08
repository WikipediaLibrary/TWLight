# -*- coding: utf-8 -*-

from datetime import datetime
import factory
import json
import random
import string

from django.contrib.auth.models import User

from TWLight.users.helpers.wiki_list import WIKIS
from TWLight.users.models import Editor, UserProfile


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile
        django_get_or_create = ('user',)

    # We haven't defined UserFactory yet so we need to be explicit about the
    # import path. (If we put UserProfileFactory after user, we'd still have this
    # same problem in defining the RelatedFactory in UserFactory.)
    user = factory.SubFactory('TWLight.users.factories.UserFactory', profile=None)
    terms_of_use = True



class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = 'alice'
    email = 'alice@example.com'

    profile = factory.RelatedFactory(UserProfileFactory, 'user')

    @classmethod
    def _generate(cls, create, attrs):
        """
        We want to ensure that factory-created users have agreed to the terms
        of use; otherwise they will be unable to exercise some features and
        tests will fail for that reason.

        Since a UserProfile is created automatically by a signal after User
        creation and defaults to terms_of_use = False, we need to find and
        change it before returning.

        See http://factoryboy.readthedocs.io/en/latest/recipes.html .
        """
        user = super(UserFactory, cls)._generate(create, attrs)
        user.userprofile.terms_of_use = True
        user.userprofile.save()
        return user



class EditorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Editor
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    real_name = 'Alice Crypto'
    country_of_residence = 'Elsewhere'
    occupation = 'Cat floofer'
    affiliation = 'Institut Pasteur'
    wp_username = factory.LazyAttribute(lambda s: ''.join(
        random.choice(string.lowercase) for i in range(10)))
    wp_editcount = 42
    wp_registered = datetime.today()
    wp_sub = 318956
    wp_groups = json.dumps(['some groups'])
    wp_rights = json.dumps(['some rights'])
    home_wiki = WIKIS[0][0]
    contributions = 'Cat floofing, telemetry, fermentation'
