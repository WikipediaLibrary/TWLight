from datetime import datetime, timedelta
from faker import Faker
import random
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.users.factories import UserFactory, EditorFactory
from TWLight.users.groups import get_coordinators, get_restricted


class Command(BaseCommand):
    help = (
        "Superuser the only user, then add a number of example users and coordinators."
    )

    def add_arguments(self, parser):
        parser.add_argument("num", nargs="+", type=int)

    def handle(self, *args, **options):
        num_editors = options["num"][0]

        existing_users = User.objects.all()

        # Superuser the only user, per twlight_vagrant README instructions.
        if existing_users.count() == 0:
            raise CommandError("No users present to Superuser. " "Please login first.")
        elif existing_users.count() > 1:
            raise CommandError(
                "More than one user present. "
                "Please ensure that only one user is present."
            )
        else:
            user = existing_users[0]
            user.is_superuser = True
            user.is_staff = True
            user.save()

        for _ in range(num_editors):
            user = UserFactory(
                email=Faker(random.choice(settings.FAKER_LOCALES)).word()
                + "@example.com"
            )
            editor = EditorFactory(
                user=user,
                real_name=Faker(random.choice(settings.FAKER_LOCALES)).name(),
                country_of_residence=Faker(
                    random.choice(settings.FAKER_LOCALES)
                ).country(),
                occupation=Faker(random.choice(settings.FAKER_LOCALES)).job(),
                affiliation=Faker(random.choice(settings.FAKER_LOCALES)).company(),
                wp_editcount=random.randint(50, 2000),
                wp_registered=Faker(
                    random.choice(settings.FAKER_LOCALES)
                ).date_time_between(start_date="-10y", end_date="now", tzinfo=None),
                contributions=Faker(random.choice(settings.FAKER_LOCALES)).paragraph(
                    nb_sentences=4
                ),
            )

        # All users who aren't the superuser
        all_users = User.objects.exclude(is_superuser=True)

        # Flag wp_valid correctly if user is valid
        for user in all_users:
            date_valid = (
                datetime.today().date() - timedelta(days=182)
                >= user.editor.wp_registered
            )

            if user.editor.wp_editcount > 500 and date_valid:
                user.editor.wp_valid = True
                user.editor.save()

        # Make 5 random users coordinators
        coordinators = get_coordinators()
        for user in random.sample(list(all_users), 5):
            user.groups.add(coordinators)
            user.save()

        # Set 5 random non-coordinator users to have restricted data processing
        restricted = get_restricted()
        non_coordinators = all_users.exclude(groups__name="coordinators")
        for user in random.sample(list(non_coordinators), 5):
            user.groups.add(restricted)
            user.save()
