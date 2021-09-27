# -*- coding: utf-8 -*-
import factory

import random
from django.conf import settings
from TWLight.resources.models import Partner, Video, Suggestion


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Partner
        strategy = factory.CREATE_STRATEGY

    company_name = factory.Faker(
        "company", locale=random.choice(settings.FAKER_LOCALES)
    )
    terms_of_use = factory.Faker("uri", locale=random.choice(settings.FAKER_LOCALES))
    status = Partner.AVAILABLE  # not the default, but usually wanted in tests


class SuggestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Suggestion
        strategy = factory.CREATE_STRATEGY

    suggested_company_name = factory.Faker("pystr", max_chars=40)
    company_url = factory.Faker("url", locale=random.choice(settings.FAKER_LOCALES))


class VideoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Video
        strategy = factory.CREATE_STRATEGY

    partner = factory.SubFactory(PartnerFactory)
