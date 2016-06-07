# -*- coding: utf-8 -*-

from datetime import datetime
import factory
import json

from django.contrib.auth.models import User

from TWLight.users.helpers.wiki_list import WIKIS
from TWLight.users.models import Editor


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = 'alice'
    email = 'alice@example.com'



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
    wp_username = 'wp_alice'
    wp_editcount = 42
    wp_registered = datetime.today()
    wp_sub = 318956
    wp_groups = json.dumps(['some groups'])
    wp_rights = json.dumps(['some rights'])
    home_wiki = WIKIS[0][0]
    contributions = 'Cat floofing, telemetry, fermentation'
