# -*- coding: utf-8 -*-

import factory

from TWLight.resources.factories import PartnerFactory
from TWLight.resources.models import Partner
from TWLight.users.factories import EditorFactory

from TWLight.applications.models import Application


class ApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application
        strategy = factory.CREATE_STRATEGY

    editor = factory.SubFactory(EditorFactory)
    partner = factory.SubFactory(PartnerFactory)

    # This needs to be set for applications to resources with the
    # PROXY authorization_method.
    requested_access_duration = None
