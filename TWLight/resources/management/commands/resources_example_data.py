import copy
from django_countries import countries
from faker import Faker
import random
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.resources.factories import (
    PartnerFactory,
    StreamFactory,
    VideoFactory,
    SuggestionFactory,
)
from TWLight.resources.models import Language, Partner, Stream, Suggestion, AccessCode


class Command(BaseCommand):
    help = "Adds a number of example resources, streams, suggestions, and tags."

    def add_arguments(self, parser):
        parser.add_argument("num", nargs="+", type=int)

    def handle(self, *args, **options):
        num_partners = options["num"][0]
        tag_list = [
            "science",
            "humanities",
            "social science",
            "history",
            "law",
            "video",
            "multidisciplinary",
        ]

        coordinators = User.objects.filter(groups__name="coordinators")
        non_proxy_auth_methods = [Partner.EMAIL, Partner.CODES, Partner.LINK]
        non_bundle_auth_methods = non_proxy_auth_methods + [Partner.PROXY]
        all_auth_methods = non_bundle_auth_methods + [Partner.BUNDLE]

        for _ in range(num_partners):
            # Choose a random authorization method for this partner
            auth_method = random.choice(all_auth_methods)

            # Basic information that all partners will have
            partner = PartnerFactory(
                company_location=random.choice(list(countries)),
                short_description=Faker(
                    random.choice(settings.FAKER_LOCALES)
                ).paragraph(nb_sentences=4),
                mutually_exclusive=False,
                authorization_method=auth_method
            )

            # We only have send instructions if this isn't a proxy partner
            if auth_method in non_proxy_auth_methods:
                partner.send_instructions = Faker(
                    random.choice(settings.FAKER_LOCALES)
                ).paragraph(nb_sentences=2)

            # Bundle partners don't require extra information, but others might.
            # They also have coordinators, can have streams, and have renewals
            if auth_method in non_bundle_auth_methods:
                partner.real_name = self.chance(True, False, 40)
                partner.country_of_residence = self.chance(True, False, 20)
                partner.specific_title = self.chance(True, False, 10)
                partner.occupation = self.chance(True, False, 10)
                partner.affiliation = self.chance(True, False, 10)
                partner.agreement_with_terms_of_use = self.chance(True, False, 10)
                partner.coordinator = random.choice(coordinators)
                partner.specific_stream = self.chance(True, False, 10)
                partner.renewals_available = random.choice([True, False])

            # Partners accessed via proxy need a target URL and requested_access_duration=True
            if auth_method not in non_proxy_auth_methods:
                partner.target_url = "https://example.com"
            if auth_method == Partner.PROXY:
                partner.requested_access_duration = True

            # LINK and CODES partners need email instructions
            if auth_method in [Partner.CODES, Partner.LINK]:
                partner.user_instructions = "User instructions email text."

            partner.save()

            # ManyToMany relationships can't be set until the partner object has
            # been created.
            random_languages = random.sample(
                list(Language.objects.all()), random.randint(1, 2)
            )

            for lang in random_languages:
                partner.languages.add(lang)

            partner.save()

        all_partners = Partner.even_not_available.all()
        for partner in all_partners:
            for tag in random.sample(tag_list, random.randint(1, 4)):
                partner.tags.add(tag)

        all_non_proxy_partners = Partner.objects.filter(
            authorization_method__in=non_proxy_auth_methods
        )
        all_non_bundle_partners = Partner.objects.filter(
            authorization_method__in=non_bundle_auth_methods
        )

        # Set 5 partners to need a registration URL. We do this separately
        # because it requires both the account_email and registration_url
        # fields to be set concurrently.
        for registration_partner in random.sample(list(all_non_proxy_partners), 5):
            registration_partner.account_email = True
            registration_partner.registration_url = Faker(
                random.choice(settings.FAKER_LOCALES)
            ).uri()
            registration_partner.save()

        # While most fields can be set at random, we want to make sure we
        # get partners with certain fields set to particular values.

        # Set 5 random partners to be unavailable
        for unavailable_partner in random.sample(list(all_partners), 5):
            unavailable_partner.status = Partner.NOT_AVAILABLE
            unavailable_partner.save()

        # Set 5% random partners to have excerpt limit in words
        for words in random.sample(list(all_partners), 10):
            words.excerpt_limit = random.randint(100, 250)
            words.save()

        # Set 5% random partners to have excerpt limit in percentage
        for percentage in random.sample(list(all_partners), 10):
            percentage.excerpt_limit_percentage = random.randint(5, 50)
            percentage.save()

        # Set 1 random partner to have excerpt limits both in words and percentage
        for percentage_words in random.sample(list(all_partners), 1):
            percentage_words.excerpt_limit_percentage = random.randint(5, 50)
            percentage_words.excerpt_limit = random.randint(100, 250)
            percentage_words.save()

        available_partners = all_partners.exclude(status=Partner.NOT_AVAILABLE)

        # Set 10 random available partners to be waitlisted
        for waitlisted_partner in random.sample(list(all_non_proxy_partners), 10):
            waitlisted_partner.status = Partner.WAITLIST
            waitlisted_partner.save()

        # Set 25 random partners to have a long description
        for long_description in random.sample(list(all_partners), 25):
            long_description.description = Faker(
                random.choice(settings.FAKER_LOCALES)
            ).paragraph(nb_sentences=10)
            long_description.save()

        # Set 10 random available partners to be featured
        for featured_partner in random.sample(list(all_non_bundle_partners), 10):
            featured_partner.featured = True
            featured_partner.save()

        # Random number of accounts available for all partners without streams
        for accounts in all_non_bundle_partners:
            if not accounts.specific_stream:
                accounts.accounts_available = random.randint(10, 550)
                accounts.save()

        # Give any specific_stream flagged partners streams.
        stream_partners = all_partners.filter(specific_stream=True)

        # If we happened to not create any partners with streams,
        # create one deliberately.
        if stream_partners.count() == 0:
            stream_partners = random.sample(list(all_partners), 1)
            stream_partners[0].specific_stream = True
            stream_partners[0].save()

        for partner in stream_partners:
            # Add 3 streams for each partner with streams
            for _ in range(3):
                stream = StreamFactory(
                    partner=partner,
                    name=Faker(random.choice(settings.FAKER_LOCALES)).sentence(
                        nb_words=3
                    )[
                        :-1
                    ],  # [:-1] removes full stop
                    description=Faker(random.choice(settings.FAKER_LOCALES)).paragraph(
                        nb_sentences=2
                    ),
                    # Authorization method needs to be the same as partner
                    authorization_method=partner.authorization_method
                )

        # Set 15 partners to have somewhere between 1 and 5 video tutorial URLs
        for partner in random.sample(list(all_partners), 15):
            for _ in range(random.randint(1, 5)):
                VideoFactory(
                    partner=partner,
                    tutorial_video_url=Faker(
                        random.choice(settings.FAKER_LOCALES)
                    ).url(),
                )

        # Random number of accounts available for all streams
        all_streams = Stream.objects.all()
        for each_stream in all_streams:
            each_stream.accounts_available = random.randint(10, 100)
            each_stream.save()

        # Generate a few partner suggestions with upvotes
        all_users = User.objects.exclude(is_superuser=True)
        author_user = random.choice(all_users)
        for _ in range(random.randint(3, 10)):
            suggestion = SuggestionFactory(
                description=Faker(random.choice(settings.FAKER_LOCALES)).paragraph(
                    nb_sentences=10
                ),
                author=author_user,
            )
            suggestion.save()
            suggestion.upvoted_users.add(author_user)
            random_users = random.sample(list(all_users), random.randint(1, 10))
            suggestion.upvoted_users.add(*random_users)

        # Generate access codes for CODES partners
        for partner in Partner.objects.filter(authorization_method=Partner.CODES):

            for i in range(25):
                new_access_code = AccessCode()
                new_access_code.code = "".join(
                    random.choice(string.ascii_uppercase + string.digits)
                    for _ in range(10)
                )
                new_access_code.partner = partner
                new_access_code.save()

    def chance(self, selected, default, chance):
        # A percentage chance to select something, otherwise selects
        # the default option. Used to generate data that's more
        # in line with the live site distribution.

        roll = random.randint(0, 100)
        if roll < chance:
            selection = selected
        else:
            selection = default

        return selection
