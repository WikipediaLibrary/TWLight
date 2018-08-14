import copy
from django_countries import countries
from faker import Faker
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.resources.factories import PartnerFactory, StreamFactory
from TWLight.resources.models import Language, Partner, Stream

class Command(BaseCommand):
    help = "Adds a number of example resources, streams, and tags."

    def add_arguments(self, parser):
        parser.add_argument('num', nargs='+', type=int)

    def handle(self, *args, **options):
        num_partners = options['num'][0]
        tag_list = ["science", "humanities", "social science", "history",
                    "law", "video", "multidisciplinary"]
        fake = Faker()

        coordinators = User.objects.filter(groups__name='coordinators')

        for _ in range(num_partners):
            partner = PartnerFactory(
                company_location = random.choice(list(countries)),
                renewals_available = random.choice([True, False]),
                short_description = fake.paragraph(nb_sentences=4),
                send_instructions = fake.paragraph(nb_sentences=2),
                coordinator = self.chance(
                    random.choice(coordinators), None, 20),
                real_name = self.chance(True, False, 40),
                country_of_residence = self.chance(True, False, 20),
                specific_title = self.chance(True, False, 10),
                specific_stream = self.chance(True, False, 10),
                occupation = self.chance(True, False, 10),
                affiliation = self.chance(True, False, 10),
                agreement_with_terms_of_use = self.chance(True, False, 10),
                mutually_exclusive = False
                )

            # ManyToMany relationships can't be set until the partner object has
            # been created.
            random_languages = random.sample(Language.objects.all(),
                    random.randint(1,2)
                    )

            for lang in random_languages:
                partner.languages.add(lang)

            partner.save()

        all_partners = Partner.even_not_available.all()
        for partner in all_partners:
            for tag in random.sample(tag_list, random.randint(1,4)):
                partner.tags.add(tag)

        # Set 5 partners to need a registration URL. We do this separately
        # because it requires both the account_email and registration_url
        # fields to be set concurrently.
        for registration_partner in random.sample(all_partners, 5):
            registration_partner.account_email = True
            registration_partner.registration_url = fake.uri()
            registration_partner.save()

        # While most fields can be set at random, we want to make sure we
        # get partners with certain fields set to particular values.

        # Set 5 random partners to be unavailable
        for unavailable_partner in random.sample(all_partners, 5):
            unavailable_partner.status = Partner.NOT_AVAILABLE
            unavailable_partner.save()
            
        # Set 5% random partners to have excerpt limit in words
        for words in random.sample(all_partners, 10):
            words.excerpt_limit = random.randint(100, 250)
            words.save()
            
        # Set 5% random partners to have excerpt limit in words
        for percentage in random.sample(all_partners, 10):
            percentage.excerpt_limit_percentage = random.randint(5, 50)
            percentage.save()
            
        # Set 1 random partner to have excerpt limits both in words and percentage
        for percentage_words in random.sample(all_partners, 1):
            percentage_words.excerpt_limit_percentage = random.randint(5, 50)
            percentage_words.excerpt_limit = random.randint(100, 250)
            percentage_words.save()
            
        available_partners = all_partners.exclude(status= Partner.NOT_AVAILABLE)

        # Set 10 random available partners to be waitlisted
        for waitlisted_partner in random.sample(available_partners, 10):
            waitlisted_partner.status = Partner.WAITLIST
            waitlisted_partner.save()

        # Set 25 random partners to have a long description
        for long_description in random.sample(all_partners, 25):
            long_description.description = fake.paragraph(nb_sentences = 10)
            long_description.save()

        # Set 10 random available partners to be featured
        for featured_partner in random.sample(available_partners, 10):
            featured_partner.featured = True
            featured_partner.save()

        # Give any specific_stream flagged partners streams.
        stream_partners = all_partners.filter(specific_stream=True)

        # If we happened to not create any partners with streams,
        # create one deliberately.
        if stream_partners.count() == 0:
            stream_partners[0].specific_stream = True
            stream_partners[0].save()

        for partner in stream_partners:
            for _ in range(3):
                stream = StreamFactory(
                    partner= partner,
                    name= fake.sentence(nb_words= 3)[:-1], # [:-1] removes full stop
                    description= fake.paragraph(nb_sentences=2)
                    )

    def chance(self, selected, default, chance):
        # A percentage chance to select something, otherwise selects
        # the default option. Used to generate data that's more
        # in line with the live site distribution.

        roll = random.randint(0,100)
        if roll < chance:
            selection = selected
        else:
            selection = default

        return selection
