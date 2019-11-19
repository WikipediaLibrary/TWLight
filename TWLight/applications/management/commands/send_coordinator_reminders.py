import logging
from collections import Counter
from django.core.management.base import BaseCommand, CommandError
from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.applications.signals import Reminder
from TWLight.applications.views import ListApplicationsView

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--app_status", type=str, required=True)

    def handle(self, *args, **options):
        if options["app_status"] == "PENDING":
            # This is not DRY. Originally, this pulled the queryset from
            # TWLight.applications.views.ListApplicationsView.get_queryset().
            # But that now expects a request object. So, we did a copy/paste.
            # We're actually getting apps with a status of PENDING or QUESTION
            # for partners with a status of AVAILABLE or WAITLIST.
            pending_apps = (
                Application.objects.filter(
                    status__in=[Application.PENDING, Application.QUESTION],
                    partner__status__in=[Partner.AVAILABLE, Partner.WAITLIST],
                    editor__isnull=False,
                )
                .exclude(editor__user__groups__name="restricted")
                .order_by("status", "partner", "date_created")
            )

            # A deduplicated dict of coordinators from the pending app queryset, along
            # with a count of how many total pending apps they have
            coordinators = Counter(
                pending_apps.values_list(
                    "partner__coordinator__editor__wp_username",
                    "partner__coordinator__email",
                    "partner__coordinator__editor__user__userprofile__lang",
                )
            )

            for coordinator, count in coordinators.items():
                # Only bother with the signal if we have a coordinator email.
                if coordinator[1]:
                    Reminder.coordinator_reminder.send(
                        sender=self.__class__,
                        app_status=options["app_status"],
                        app_count=count,
                        coordinator_wp_username=coordinator[0],
                        coordinator_email=coordinator[1],
                        coordinator_lang=coordinator[2],
                    )
