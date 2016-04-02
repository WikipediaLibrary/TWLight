# -*- coding: utf-8 -*-

import factory

from TWLight.resources.models import Partner


class PartnerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Partner
        strategy = factory.CREATE_STRATEGY

    company_name = 'Publisher McPubface'
