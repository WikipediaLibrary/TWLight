# -*- coding: utf-8 -*-

import factory

from TWLight.resources.models import Partner, Stream, Video


class PartnerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Partner
        strategy = factory.CREATE_STRATEGY

    company_name = factory.Faker('company')
    terms_of_use = factory.Faker('uri')
    status = Partner.AVAILABLE # not the default, but usually wanted in tests



class StreamFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Stream
        strategy = factory.CREATE_STRATEGY

    partner = factory.SubFactory(PartnerFactory)
    name = factory.Faker('bs')



class VideoFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Video
        strategy = factory.CREATE_STRATEGY

    partner = factory.SubFactory(PartnerFactory)
