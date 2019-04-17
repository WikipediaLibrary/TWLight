import datetime
from dateutil.relativedelta import relativedelta
from faker import Faker
import random
from mock import patch

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.applications.views import SendReadyApplicationsView
from TWLight.resources.models import Partner, Stream, AccessCode

def logged_in_example_coordinator(client, coordinator):
    """
    Creates a logged in coordinator user. Compacted version of EditorCraftRoom
    used in tests.
    """
    terms_url = reverse('terms')

    coordinator.set_password('editor')
    coordinator.save()

    # Log user in
    client = Client(SERVER_NAME='twlight.vagrant.localdomain')
    session = client.session
    client.login(username=coordinator.username, password='editor')

    coordinator.terms_of_use = True

    return coordinator

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

        # We want to flag applications as SENT via a client later, so let's only
        # automatically give applications non-Sent statuses.
        valid_choices = [Application.PENDING, Application.QUESTION,
            Application.APPROVED, Application.NOT_APPROVED, Application.INVALID]

        for _ in range(num_applications):
            random_user = random.choice(all_users)
            # Limit to partners this user hasn't already applied to.
            not_applied_partners = available_partners.exclude(
                applications__editor=random_user.editor
                )
            random_partner = random.choice(not_applied_partners)

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
                app.status = random.choice(valid_choices)

                # Figure out earliest valid date for this app
                if random_user.editor.wp_registered < import_date.date():
                    start_date = import_date
                else:
                    start_date = random_user.editor.wp_registered

                app.date_created = fake.date_time_between(
                    start_date = start_date,
                    end_date = "now",
                    tzinfo=None)
                app.rationale = fake.paragraph(nb_sentences=3)
                app.comments = fake.paragraph(nb_sentences=2)

            # For closed applications, assign date_closed and date_open
            if app.status in Application.FINAL_STATUS_LIST:
                if not imported:
                    potential_end_date = app.date_created + relativedelta(years=1)
                    if potential_end_date > datetime.datetime.now():
                        end_date = "now"
                    else:
                        end_date = potential_end_date
                    app.date_closed = fake.date_time_between(
                        start_date = app.date_created,
                        end_date = end_date,
                        tzinfo=None)
                    app.days_open = (app.date_closed - app.date_created).days

            app.save()

        # Let's mark all Approved applications that were approved more
        # than 3 weeks ago as Sent.
        old_approved_apps = Application.objects.filter(
            status=Application.APPROVED,
            date_created__lte=datetime.datetime.now() - relativedelta(weeks=3)
            )

        # We need to be able to handle messages
        message_patcher = patch('TWLight.applications.views.messages.add_message')
        message_patcher.start()
        for approved_app in old_approved_apps:
            client = Client(SERVER_NAME='twlight.vagrant.localdomain')
            coordinator = logged_in_example_coordinator(client, approved_app.partner.coordinator)

            this_partner_access_codes = AccessCode.objects.filter(
                                partner=approved_app.partner,
                                authorization__isnull=True)

            url = reverse('applications:send_partner',
                kwargs={'pk': approved_app.partner.pk})

            if approved_app.partner.authorization_method == Partner.EMAIL:
                request = RequestFactory().post(url,
                    data={'applications': [approved_app.pk]})

            # If this partner has access codes, assign a code to
            # this sent application.
            elif approved_app.partner.authorization_method == Partner.CODES:
                access_code = random.choice(this_partner_access_codes)
                request = RequestFactory().post(url,
                            data={'accesscode': ["{app_pk}_{code}".format(
                                app_pk=approved_app.pk,
                                code=access_code.code)]})

            request.user = coordinator

            response = SendReadyApplicationsView.as_view()(
                request, pk=approved_app.partner.pk)

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
