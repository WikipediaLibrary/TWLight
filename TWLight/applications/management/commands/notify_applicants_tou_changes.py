import logging

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from TWLight.helpers import site_id
from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from django_comments.models import Comment

logger = logging.getLogger(__name__)

twl_team = User.objects.get(username="TWL Team")


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Get apps with a status of PENDING or QUESTION for partners with a status of AVAILABLE
        # where the editor has not agreed to the terms of use.
        pending_apps = (
            Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION],
                partner__status__in=[Partner.AVAILABLE],
                editor__isnull=False,
                editor__user__userprofile__terms_of_use=False,
            )
            .exclude(editor__user__groups__name="restricted")
            .order_by("status", "partner", "date_created")
        )

        # Loop through the apps and add a comment if twl_team hasn't commented already or if the app hasn't had comments
        # in 8 days or more.
        for app in pending_apps:
            if (
                Comment.objects.filter(
                    Q(object_pk=str(app.pk), site_id=site_id()),
                    (
                        Q(user=twl_team)
                        | Q(submit_date__gte=(timezone.now() - timedelta(days=8)))
                    ),
                ).count()
                == 0
            ):
                comment = Comment(
                    content_object=app,
                    site_id=site_id(),
                    user=twl_team,
                    # fmt: off
                    # Translators: This comment is added to pending applications when our terms of use change.
                    comment=_("Our terms of use have changed. Your applications will not be processed until you log in and agree to our updated terms."),
                    # fmt: on
                )
                comment.save()
