# -*- coding: utf-8 -*-

import factory

from TWLight.resources.models import Partner, Stream


class PartnerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Partner
        strategy = factory.CREATE_STRATEGY

    company_name = 'Publisher McPubface'
    terms_of_use = 'https://example.com/terms'
    status = Partner.AVAILABLE # not the default, but usually wanted in tests



class StreamFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Stream
        strategy = factory.CREATE_STRATEGY

    partner = factory.SubFactory(PartnerFactory)
    name = 'Dancing about Architecture'
