from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

from TWLight.helpers import site_id
from django.dispatch import receiver, Signal
from django.db.models.signals import pre_save, post_save
from django_comments.signals import comment_was_posted
from django_comments.models import Comment
from django.contrib.auth.models import User
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _
from TWLight.resources.models import Partner
from TWLight.applications.models import Application
from TWLight.users.models import Authorization

no_more_accounts = Signal(providing_args=["partner_pk"])

logger = logging.getLogger(__name__)


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


# IMPORTANT: pre_save is not sent by Queryset.update(), so *none of this
# behavior will happen on if you update() an Application queryset*.
# That is sometimes okay, but it is not always okay.
# Errors caused by days_open not existing when expected to
# exist can show up in weird parts of the application (for example, template
# rendering failing when get_num_days_open returns None but its output is
# passed to a template filter that needs an integer).
@receiver(pre_save, sender=Application)
def update_app_status_on_save(sender, instance, **kwargs):

    # Make sure not using a mix of dates and datetimes
    if instance.date_created and isinstance(instance.date_created, datetime):
        instance.date_created = instance.date_created.date()

    # Make sure not using a mix of dates and datetimes
    if instance.date_closed and isinstance(instance.date_closed, datetime):
        instance.date_closed = instance.date_closed.date()

    if instance.id:
        orig_app = Application.include_invalid.get(pk=instance.id)
        orig_status = orig_app.status
        if all(
            [
                orig_status not in Application.FINAL_STATUS_LIST,
                int(instance.status) in Application.FINAL_STATUS_LIST,
                not bool(instance.date_closed),
            ]
        ):

            instance.date_closed = localtime(now()).date()
            instance.days_open = (instance.date_closed - instance.date_created).days

    else:
        # If somehow we've created an Application whose status is final
        # at the moment of creation, set its date-closed-type parameters
        # too.
        if (
            instance.status in Application.FINAL_STATUS_LIST
            and not instance.date_closed
        ):

            instance.date_closed = localtime(now()).date()
            instance.days_open = 0


@receiver(post_save, sender=Application)
def post_revision_commit(sender, instance, **kwargs):

    # For some authorization methods, we can skip the manual Approved->Sent
    # step and just immediately take an Approved application and give it
    # a finalised status.
    skip_approved = (
        instance.status == Application.APPROVED and instance.is_instantly_finalized()
    )

    if skip_approved:
        instance.status = Application.SENT
        instance.save()

    # Renewals are for applications that are approved/sent.
    # Having a parent for NOT_APPROVED apps hinders us from
    # correctly renewing the parent. So, we unset the parent
    # if the status is NOT_APPROVED and the app already has
    # a parent.
    if instance.status == Application.NOT_APPROVED and instance.parent:
        instance.parent = None
        instance.save()

    # Authorize editor to access resource after an application is saved as sent.

    if instance.status == Application.SENT:
        # Check if an authorization already exists.
        existing_authorization = Authorization.objects.filter(
            user=instance.user, partners=instance.partner
        )

        authorized_user = instance.user
        authorizer = instance.sent_by

        # In the case that there is no existing authorization, create a new one
        if existing_authorization.count() == 0:
            authorization = Authorization()
        # If an authorization already existed (such as in the case of a
        # renewal), we'll simply update that one.
        elif existing_authorization.count() == 1:
            authorization = existing_authorization[0]
        else:
            logger.error(
                "Found more than one authorization object for "
                "{user} - {partner}".format(
                    user=instance.user, partner=instance.partner
                )
            )
            return

        authorization.user = authorized_user
        authorization.authorizer = authorizer

        # If this is a proxy partner, and the requested_access_duration
        # field is set to false, set (or reset) the expiry date
        # to one year from now
        if (
            instance.partner.authorization_method == Partner.PROXY
            and instance.requested_access_duration is None
        ):
            one_year_from_now = date.today() + timedelta(days=365)
            authorization.date_expires = one_year_from_now
        # If this is a proxy partner, and the requested_access_duration
        # field is set to true, set (or reset) the expiry date
        # to 1, 3, 6 or 12 months from today based on user input
        elif (
            instance.partner.authorization_method == Partner.PROXY
            and instance.partner.requested_access_duration is True
        ):
            custom_expiry_date = date.today() + relativedelta(
                months=instance.requested_access_duration
            )
            authorization.date_expires = custom_expiry_date
        # Alternatively, if this partner has a specified account_length,
        # we'll use that to set the expiry.
        elif instance.partner.account_length:
            # account_length should be a timedelta
            authorization.date_expires = date.today() + instance.partner.account_length
        authorization.save()
        authorization.partners.add(instance.partner)

        # If we just finalised a renewal, reset reminder_email_sent
        # so that we can send further reminders.
        if instance.parent and authorization.reminder_email_sent:
            authorization.reminder_email_sent = False
            authorization.save()


@receiver(post_save, sender=Partner)
def invalidate_bundle_partner_applications(sender, instance, **kwargs):
    """
    Invalidates open applications for bundle partners.
    """

    twl_team = User.objects.get(username="TWL Team")

    if sender == Partner:
        partner = instance

    if partner and partner.authorization_method == Partner.BUNDLE:
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
            comment = Comment.objects.create(
                content_object=application,
                site_id=site_id(),
                user=twl_team,
                # fmt: off
                # Translators: This comment is added to open applications when a partner joins the Library Bundle, which does not require applications.
                comment=_("This partner joined the Library Bundle, which does not require applications. This application will be marked as invalid."),
                # fmt: on
            )
            comment.save()
            # Mark application invalid.
            application.status = Application.INVALID
            application.save()
