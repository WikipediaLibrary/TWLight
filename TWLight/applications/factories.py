# -*- coding: utf-8 -*-

import factory

from TWLight.resources.factories import PartnerFactory
from TWLight.users.factories import UserFactory

from TWLight.applications.models import Application


class ApplicationFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Application
        strategy = factory.CREATE_STRATEGY

    user = factory.SubFactory(UserFactory)
    partner = factory.SubFactory(PartnerFactory)
