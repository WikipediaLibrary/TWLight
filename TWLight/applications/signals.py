import logging

from django.conf import settings
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django_comments.signals import comment_was_posted
from django_comments.models import Comment
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from TWLight.resources.models import Partner, Stream
from .models import Application

no_more_accounts = Signal(providing_args=["partner_pk"])

logger = logging.getLogger(__name__)

twl_team, created = User.objects.get_or_create(
    username="TWL Team", email="wikipedialibrary@wikimedia.org"
)


class Reminder(object):
    coordinator_reminder = Signal(
        providing_args=[
            "app_status",
            "app_count",
            "coordinator_wp_username",
            "coordinator_email",
            "coordinator_lang",
        ]
    )


@receiver(comment_was_posted)
def under_discussion(sender, comment, request, **kwargs):
    """
    When coordinators post a comment on an application which currently has the
    PENDING status, automatically set it to 'Under discussion' (QUESTION).
    """
    try:
        application_object = Application.objects.get(pk=comment.object_pk)
        if (
            application_object.status == Application.PENDING
            and application_object.editor.user.username != request.user.username
            and application_object.partner.authorization_method != Partner.BUNDLE
        ):
            application_object.status = Application.QUESTION
            application_object.save()
    except Application.DoesNotExist:
        logger.info(
            "Status of invalid application not changed on comment {}.".format(
                comment.object_pk
            )
        )
        pass


@receiver(no_more_accounts)
def set_partner_status(sender, **kwargs):
    """
    Whenever an application is approved (except for in BatchEditView)
    we do some calculations to see if we've run out of accounts. If 
    we have, we mark the partner as waitlisted if not, continue.
    """
    partner_pk = kwargs["partner_pk"]
    try:
        partner = Partner.objects.get(pk=partner_pk)
        partner.status = Partner.WAITLIST
        partner.save()
    except Partner.DoesNotExist:
        logger.info(
            "set_partner_status signal received, but"
            " partner {pk} does not exist - unable to set"
            " partner status".format(pk=partner_pk)
        )


@receiver(post_save, sender=Partner)
@receiver(post_save, sender=Stream)
def invalidate_bundle_partner_applications(sender, instance, **kwargs):
    """
    Invalidates open applications for bundle partners.
    """

    if sender == Partner:
        partner = instance
    elif sender == Stream:
        partner = instance.partner

    if partner.authorization_method == Partner.BUNDLE:
        # All open applications for this partner.
        applications = Application.objects.filter(
            partner=partner,
            status__in=(
                Application.PENDING,
                Application.QUESTION,
                Application.APPROVED,
            ),
        )

        for application in applications:
            # Add a comment.
            comment = Comment(
                content_object=application,
                site_id=settings.SITE_ID,
                user=twl_team,
                # Translators: This comment is added to open applications when a partner joins the Library Bundle, which does not require applications.
                comment=_(
                    "This partner joined the Library Bundle, which does not require applications."
                    "This application will be marked as invalid."
                ),
            )
            comment.save()
            # Mark application invalid.
            application.status = Application.INVALID
            application.save()
