import datetime
from dateutil.relativedelta import relativedelta
from faker import Faker
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.models import Partner, Stream, AccessCode

class Command(BaseCommand):
    help = "Adds a number of example applications."

    def add_arguments(self, parser):
        parser.add_argument('num', nargs='+', type=int)

    def handle(self, *args, **options):
        num_applications = options['num'][0]
        fake = Faker()

        available_partners = Partner.objects.all()
        # Don't fire any applications from the superuser.
        all_users = User.objects.exclude(is_superuser=True)

        import_date = datetime.datetime(2017, 7, 17, 0, 0, 0)

        for _ in range(num_applications):
            random_user = random.choice(all_users)
            random_partner = random.choice(available_partners)

            app = ApplicationFactory(
                editor = random_user.editor,
                partner = random_partner,
                hidden = self.chance(True, False, 10)
                )

            # Make sure partner-specific information is filled.
            if random_partner.specific_stream:
                app.specific_stream = random.choice(
                    Stream.objects.filter(partner=random_partner))

            if random_partner.specific_title:
                app.specific_title = fake.sentence(nb_words= 3)

            if random_partner.agreement_with_terms_of_use:
                app.agreement_with_terms_of_use = True

            if random_partner.account_email:
                app.account_email = fake.email()

            # Imported applications have very specific information, and were
            # all imported on the same date.
            imported = self.chance(True, False, 50)

            if imported:
                app.status = Application.SENT
                app.date_created = import_date
                app.date_closed = import_date
                app.rationale = "Imported on 2017-07-17"
                app.comments = "Imported on 2017-07-17"
                app.imported = True
            else:
                app.status = random.choice(Application.STATUS_CHOICES)[0]
                app.date_created = fake.date_time_between(
                    start_date = random_user.editor.wp_registered,
                    end_date = "now",
                    tzinfo=None)
                app.rationale = fake.paragraph(nb_sentences=3)
                app.comments = fake.paragraph(nb_sentences=2)

            # For closed applications, assign date_closed and date_open
            if app.status in Application.FINAL_STATUS_LIST:
                if not imported:
                    app.date_closed = fake.date_time_between(
                        start_date = app.date_created,
                        end_date = app.date_created + relativedelta(years=1),
                        tzinfo=None)
                    app.days_open = (app.date_closed - app.date_created).days

            if app.status == Application.SENT:
                # Assign sent_by if this is a non-imported sent applications
                if not imported:
                    app.sent_by = random_partner.coordinator

                # If this partner has access codes, assign a code to
                # this sent application.
                if random_partner.authorization_method == Partner.CODES:
                    this_partner_access_codes = AccessCode.objects.filter(
                        partner=random_partner,
                        authorization__isnull=True)
                    app_code = random.choice(this_partner_access_codes)
                    #app_code.application = app
                    app_code.save()
            app.save()

        # Renew a selection of sent apps.
        all_apps = Application.objects.filter(status=Application.SENT)
        num_to_renew = int(all_apps.count()*0.5)
        for app_to_renew in random.sample(all_apps, num_to_renew):
            app_to_renew.renew()

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
