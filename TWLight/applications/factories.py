# -*- coding: utf-8 -*-

import factory

from TWLight.resources.factories import PartnerFactory
from TWLight.users.factories import EditorFactory

from TWLight.applications.models import Application


class ApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application
        strategy = factory.CREATE_STRATEGY

    editor = factory.SubFactory(EditorFactory)
    partner = factory.SubFactory(PartnerFactory)
