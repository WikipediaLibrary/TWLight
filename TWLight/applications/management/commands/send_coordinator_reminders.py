import logging
from collections import Counter
from django.core.management.base import BaseCommand
from django.db.models import Q

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.applications.signals import Reminder
from TWLight.users.models import Editor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # This is not DRY. Originally, this pulled the queryset from
        # TWLight.applications.views.ListApplicationsView.get_queryset().
        # But that now expects a request object. So, we did a copy/paste.
        # We're actually getting apps with a status of PENDING or QUESTION
        # or APPROVED, and their corresponding user preferences being True
        # for partners with a status of AVAILABLE.
        all_apps = (
            Application.objects.filter(
                Q(
                    partner__coordinator__editor__user__userprofile__pending_app_reminders=True
                )
                & Q(status=Application.PENDING)
                | Q(
                    partner__coordinator__editor__user__userprofile__discussion_app_reminders=True
                )
                & Q(status=Application.QUESTION)
                | Q(
                    partner__coordinator__editor__user__userprofile__approved_app_reminders=True
                )
                & Q(status=Application.APPROVED),
                partner__status__in=[Partner.AVAILABLE],
                editor__isnull=False,
            )
            .exclude(editor__user__groups__name="restricted")
            .order_by("status", "partner", "date_created")
        )
        # A deduplicated dict of coordinators from the pending app queryset, along
        # with a count of how many total pending apps they have
        coordinators = Counter(
            all_apps.values_list(
                "partner__coordinator__editor",
                "partner__coordinator__email",
                "partner__coordinator__editor__user__userprofile__lang",
            )
        )

        for coordinator, count in list(coordinators.items()):
            try:
                # We create a dictionary with the three status codes
                # we'd want to send emails for, and their corresponding
                # counts.
                app_status_and_count = {
                    Application.PENDING: all_apps.filter(
                        status=Application.PENDING,
                        partner__coordinator__editor=coordinator[0],
                    ).count(),
                    Application.QUESTION: all_apps.filter(
                        status=Application.QUESTION,
                        partner__coordinator__editor=coordinator[0],
                    ).count(),
                    Application.APPROVED: all_apps.filter(
                        status=Application.APPROVED,
                        partner__coordinator__editor=coordinator[0],
                    ).count(),
                }
                editor = Editor.objects.get(id=coordinator[0])
            except Editor.DoesNotExist:
                logger.info(
                    "Editor {} does not exist; skipping.".format(coordinator[0])
                )
                break
            # Only bother with the signal if we have a coordinator email.
            if coordinator[1]:
                Reminder.coordinator_reminder.send(
                    sender=self.__class__,
                    app_status_and_count=app_status_and_count,
                    coordinator_wp_username=editor.wp_username,
                    coordinator_email=coordinator[1],
                    coordinator_lang=coordinator[2],
                )
