import logging
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from django_comments.models import Comment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Get apps with a status of PENDING or QUESTION for partners with a status of AVAILABLE or WAITLIST
        # where the editor has not agreed to the terms of use.
        pending_apps = (
            Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION],
                partner__status__in=[Partner.AVAILABLE, Partner.WAITLIST],
                editor__isnull=False,
                agreement_with_terms_of_use=False
            )
                .exclude(editor__user__groups__name="restricted")
                .order_by("status", "partner", "date_created")
        )

        # Loop through the apps and add a comment.
        for app in pending_apps:
            comment = Comment(
                content_object=app,
                site_id=settings.SITE_ID,
                # Translators: This comment is added to pending applications when our terms of use change.
                comment=_("Our terms of use have changed. "
                          "Your applications will not be processed until you log in and agree to our updated terms.")
            )
            comment.save()
