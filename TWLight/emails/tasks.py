"""
TWLight email sending.

TWLight generates and sends emails using https://bameda.github.io/djmail/ .
Any view that wishes to send an email should do so using a task defined here.

Templates for these emails are available in emails/templates/emails. djmail
will look for files named {{ name }}-body-html.html, {{ name }}-body-text.html,
and {{ name }}-subject.html, where {{ name }} is the name attribute of the
TemplateMail subclass.

Email templates are normal Django templates. This means two important things:
1) They can be rendered with context;
2) They can use {% trans %} and {% blocktrans trimmed %}. In fact, they _should_, to
   support internationalization.

Add a 'lang' attribute to the context passed into TemplateMail in order to
specify which language to render the template in.

There is no need to faff about with Celery in this file. djmail will decide
whether to send synchronously or asynchronously based on the value of
settings.DJMAIL_REAL_BACKEND.
"""
from djmail import template_mail
from djmail.template_mail import MagicMailBuilder, InlineCSSTemplateMail
import logging
from reversion.models import Version

from django_comments.models import Comment
from django_comments.signals import comment_was_posted
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse_lazy
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404

from TWLight.applications.models import Application
from TWLight.applications.signals import Reminder
from TWLight.emails.signals import ContactUs
from TWLight.resources.models import AccessCode, Partner
from TWLight.users.groups import get_restricted
from TWLight.users.signals import Notice


logger = logging.getLogger(__name__)


# COMMENT NOTIFICATION
# ------------------------------------------------------------------------------


class CommentNotificationEmailEditors(template_mail.TemplateMail):
    name = "comment_notification_editors"


class CommentNotificationCoordinators(template_mail.TemplateMail):
    name = "comment_notification_coordinator"


class CommentNotificationEmailOthers(template_mail.TemplateMail):
    name = "comment_notification_others"


class ApprovalNotification(template_mail.TemplateMail):
    name = "approval_notification"


class WaitlistNotification(template_mail.TemplateMail):
    name = "waitlist_notification"


class RejectionNotification(template_mail.TemplateMail):
    name = "rejection_notification"


class CoordinatorReminderNotification(template_mail.TemplateMail):
    name = "coordinator_reminder_notification"


class UserRenewalNotice(template_mail.TemplateMail):
    name = "user_renewal_notice"


@receiver(Reminder.coordinator_reminder)
def send_coordinator_reminder_emails(sender, **kwargs):
    """
    Any time the related management command is run, this sends email to the
    to designated coordinators, reminding them to login
    to the site if there are pending applications.
    """
    app_status_and_count = kwargs["app_status_and_count"]
    pending_count = None
    question_count = None
    approved_count = None
    total_apps = 0
    # We unwrap app_status_and_count and take stock of the data
    # in a way that's convenient for us to use in email.send
    for status, count in app_status_and_count.items():
        if count != 0 and status == Application.PENDING:
            pending_count = count
            total_apps += count
        if count != 0 and status == Application.QUESTION:
            question_count = count
            total_apps += count
        if count != 0 and status == Application.APPROVED:
            approved_count = count
            total_apps += count

    coordinator_wp_username = kwargs["coordinator_wp_username"]
    coordinator_email = kwargs["coordinator_email"]
    coordinator_lang = kwargs["coordinator_lang"]
    base_url = get_current_site(None).domain
    path = reverse_lazy("applications:list")
    link = "https://{base}{path}".format(base=base_url, path=path)

    logger.info(
        "Received coordinator reminder signal for {coordinator_wp_username}; "
        "preparing to send reminder email.".format(
            coordinator_wp_username=coordinator_wp_username
        )
    )
    email = CoordinatorReminderNotification()
    logger.info("Email constructed.")
    email.send(
        coordinator_email,
        {
            "user": coordinator_wp_username,
            "lang": coordinator_lang,
            "pending_count": pending_count,
            "question_count": question_count,
            "approved_count": approved_count,
            "total_apps": total_apps,
            "link": link,
        },
    )
    logger.info("Email queued.")


@receiver(Notice.user_renewal_notice)
def send_user_renewal_notice_emails(sender, **kwargs):
    """
    Any time the related managment command is run, this sends email to
    users who have authorizations that are soon to expire.
    """
    user_wp_username = kwargs["user_wp_username"]
    user_email = kwargs["user_email"]
    user_lang = kwargs["user_lang"]
    partner_name = kwargs["partner_name"]
    path = kwargs["partner_link"]

    base_url = get_current_site(None).domain
    partner_link = "https://{base}{path}".format(base=base_url, path=path)

    email = UserRenewalNotice()

    email.send(
        user_email,
        {
            "user": user_wp_username,
            "lang": user_lang,
            "partner_name": partner_name,
            "partner_link": partner_link,
        },
    )


@receiver(comment_was_posted)
def send_comment_notification_emails(sender, **kwargs):
    """
    Any time a comment is posted on an application, this sends email to the
    application owner and anyone else who previously commented.
    """
    current_comment = kwargs["comment"]
    app = current_comment.content_object
    assert isinstance(app, Application)

    logger.info(
        "Received comment signal on app number {app.pk}; preparing "
        "to send notification emails".format(app=app)
    )

    if "request" in kwargs:
        # This is the expected case; the comment_was_posted signal should send
        # this.
        request = kwargs["request"]
    else:
        # But if there's no request somehow, get_current_site has a sensible
        # default.
        request = None

    base_url = get_current_site(request).domain
    logger.info("Site base_url is {base_url}".format(base_url=base_url))
    app_url = "https://{base}{path}".format(base=base_url, path=app.get_absolute_url())
    logger.info("app_url is {app_url}".format(app_url=app_url))

    # If the editor who owns this application was not the comment poster, notify
    # them of the new comment.
    if current_comment.user != app.editor.user:
        if app.editor.user.email:
            logger.info("we should notify the editor")
            email = CommentNotificationEmailEditors()
            logger.info("email constructed")
            email.send(
                app.editor.user.email,
                {
                    "user": app.editor.wp_username,
                    "lang": app.editor.user.userprofile.lang,
                    "app": app,
                    "app_url": app_url,
                    "partner": app.partner,
                    "submit_date": current_comment.submit_date,
                    "commenter": current_comment.user.editor.wp_username,
                    "comment": current_comment.comment,
                },
            )
            logger.info(
                "Email queued for {app.editor.user.email} about "
                "app #{app.pk}".format(app=app)
            )

    # Send emails to the last coordinator to make a status change to this
    # application, as long as they aren't the ones leaving the comment.
    app_versions = Version.objects.get_for_object(app)

    # 'First' app version is the most recent
    recent_app_coordinator = app_versions.first().revision.user
    if recent_app_coordinator and recent_app_coordinator != current_comment.user:
        if recent_app_coordinator != app.partner.coordinator and not (
            recent_app_coordinator.is_staff
        ):
            recent_app_coordinator = app.partner.coordinator
        email = CommentNotificationCoordinators()
        email.send(
            recent_app_coordinator.email,
            {
                "user": recent_app_coordinator.editor.wp_username,
                "lang": recent_app_coordinator.userprofile.lang,
                "app": app,
                "app_url": app_url,
                "partner": app.partner,
                "submit_date": current_comment.submit_date,
                "commenter": current_comment.user.editor.wp_username,
                "comment": current_comment.comment,
            },
        )
        logger.info(
            "Coordinator email queued for {app.editor.user.email} about app "
            "#{app.pk}".format(app=app)
        )

    # Send to any previous commenters on the thread, other than the editor,
    # the person who left the comment just now, and the last coordinator.
    all_comments = Comment.objects.filter(
        object_pk=app.pk,
        content_type__model="application",
        content_type__app_label="applications",
    )
    users = set([comment.user for comment in all_comments])

    users.remove(current_comment.user)
    try:
        users.remove(app.editor.user)
    except KeyError:
        # If the editor is not among the prior commenters, that's fine; no
        # reason they should be.
        pass
    if recent_app_coordinator:
        try:
            users.remove(recent_app_coordinator)
        except KeyError:
            # Likewise, coordinator might not have commented.
            pass

    for user in users:
        if user:
            # Allow emails to be sent to system users with no editor object.
            if hasattr(user, "editor"):
                username = user.editor.wp_username
            else:
                username = user.username
            email = CommentNotificationEmailOthers()
            email.send(
                user.email,
                {
                    "user": username,
                    "lang": user.userprofile.lang,
                    "app": app,
                    "app_url": app_url,
                    "partner": app.partner,
                    "submit_date": current_comment.submit_date,
                    "commenter": current_comment.user.editor.wp_username,
                    "comment": current_comment.comment,
                },
            )
            logger.info(
                "Email queued for {app.editor.user.email} about app "
                "#{app.pk}".format(app=app)
            )


def send_approval_notification_email(instance):
    base_url = get_current_site(None).domain
    path = reverse_lazy("users:my_library")
    link = "https://{base}{path}".format(base=base_url, path=path)
    email = ApprovalNotification()
    # If, for some reason, we're trying to send an email to a user
    # who deleted their account, stop doing that.

    if instance.editor:
        # Emails for approved emails in access codes method shall be sent only when finalized
        if instance.partner.authorization_method == Partner.CODES:
            logger.info(
                "Email for access codes method should be sent only once,"
                "when the status of application is finalized."
            )
        else:
            email.send(
                instance.user.email,
                {
                    "user": instance.user.editor.wp_username,
                    "lang": instance.user.userprofile.lang,
                    "partner": instance.partner,
                    "link": link,
                    "user_instructions": instance.get_user_instructions(),
                },
            )
    else:
        logger.error(
            "Tried to send an email to an editor that doesn't "
            "exist, perhaps because their account is deleted."
        )


def send_waitlist_notification_email(instance):
    base_url = get_current_site(None).domain
    path = reverse_lazy("users:my_library")
    link = "https://{base}{path}".format(base=base_url, path=path)

    restricted = get_restricted()

    email = WaitlistNotification()
    if instance.editor:
        if restricted not in instance.editor.user.groups.all():
            email.send(
                instance.user.email,
                {
                    "user": instance.user.editor.wp_username,
                    "lang": instance.user.userprofile.lang,
                    "partner": instance.partner,
                    "link": link,
                },
            )
        else:
            logger.info(
                "Skipped user {username} when sending "
                "waitlist notification email because user has "
                "restricted data processing.".format(
                    username=instance.editor.wp_username
                )
            )
    else:
        logger.error(
            "Tried to send an email to an editor that doesn't "
            "exist, perhaps because their account is deleted."
        )


def send_rejection_notification_email(instance):
    base_url = get_current_site(None).domain

    if instance.pk:
        app_url = "https://{base}{path}".format(
            base=base_url, path=instance.get_absolute_url()
        )
    else:
        # If we are sending an email for a newly created instance, it won't have
        # a pk, so instance.get_absolute_url() won't return successfully.
        # This should lead to an imperfect but navigable user experience, given
        # the text of the email - it won't take them straight to their app, but
        # it will take them to a page *via which* they can perform the review
        # steps described in the email template.
        app_url = reverse_lazy("users:home")

    email = RejectionNotification()
    if instance.editor:
        email.send(
            instance.user.email,
            {
                "user": instance.user.editor.wp_username,
                "lang": instance.user.userprofile.lang,
                "partner": instance.partner,
                "app_url": app_url,
            },
        )
    else:
        logger.error(
            "Tried to send an email to an editor that doesn't "
            "exist, perhaps because their account is deleted."
        )


@receiver(pre_save, sender=Application)
def update_app_status_on_save(sender, instance, **kwargs):
    """
    If the Application's status has changed in a way that justifies sending
    email, do so. Otherwise, do nothing.
    """
    # Maps status indicators to the correct email handling function.
    handlers = {
        Application.APPROVED: send_approval_notification_email,
        Application.NOT_APPROVED: send_rejection_notification_email,
        # We can't use Partner.WAITLIST as the key, because that's actually an
        # integer, and it happens to be the same as Application.APPROVED. If
        # we're going to have a lot more keys on this list, we're going to have
        # to start thinking about namespacing them.
        "waitlist": send_waitlist_notification_email,
    }

    handler_key = None

    # Case 1: Application already existed; status has been changed.
    if instance.id:
        orig_app = Application.objects.get(pk=instance.id)
        orig_status = orig_app.status

        if orig_status != instance.status:
            handler_key = instance.status

    # Case 2: Application was just created.
    else:
        # WAITLIST is a status adhering to Partner, not to Application. So
        # to email editors when they apply to a waitlisted partner, we need
        # to check Partner status on app submission.
        # SENT is a post approval step that shouldn't be a possible status on
        # app creation under normal circumstances.

        if instance.partner.status == Partner.WAITLIST:
            handler_key = "waitlist"
        else:
            handler_key = instance.status

    if handler_key:
        try:
            # Send email if it has an email-worthy status.
            handlers[handler_key](instance)
        except KeyError:
            # This is fine - we only send emails for a few of the range of
            # possible statuses, so just continue.
            pass


@receiver(pre_save, sender=AccessCode)
def send_authorization_emails(sender, instance, **kwargs):
    """
    When access code objects are updated, check if they should trigger
    an email to a user.
    """

    # The AccessCode should already exist, don't trigger on code creation.
    if instance.id:
        orig_code = AccessCode.objects.get(pk=instance.id)
        # If this code is having an authorization added where it didn't
        # have one before, we've probably just finalised an application
        # and therefore want to send an email.
        if not orig_code.authorization and instance.authorization:
            mail_instance = MagicMailBuilder()
            email = mail_instance.access_code_email(
                instance.authorization.user.email,
                {
                    "editor_wp_username": instance.authorization.user.editor.wp_username,
                    "lang": instance.authorization.user.userprofile.lang,
                    "partner": instance.partner,
                    "access_code": instance.code,
                    "user_instructions": instance.partner.user_instructions,
                },
            )
            email.send()


@receiver(pre_save, sender=Partner)
def notify_applicants_when_waitlisted(sender, instance, **kwargs):
    """
    When Partners are switched to WAITLIST status, anyone with open applications
    should be notified.
    """
    if instance.id:
        orig_partner = get_object_or_404(Partner, pk=instance.id)

        if (
            orig_partner.status != instance.status
        ) and instance.status == Partner.WAITLIST:

            for app in orig_partner.applications.filter(
                status__in=[Application.PENDING, Application.QUESTION]
            ):
                send_waitlist_notification_email(app)


@receiver(ContactUs.new_email)
def contact_us_emails(sender, **kwargs):
    """
    Whenever a user submits a message using the contact us form
    this forwards the message to wikipedialibrary@wikimedia.org
    with some additional data.
    """
    reply_to = []
    cc = []
    user_email = kwargs["user_email"]
    editor_wp_username = kwargs["editor_wp_username"]
    body = kwargs["body"]
    reply_to.append(user_email)

    logger.info(
        "Received contact us form submit signal for {editor_wp_username}; "
        "preparing to send email to wikipedialibrary@wikimedia.org.".format(
            editor_wp_username=editor_wp_username
        )
    )

    mail_instance = MagicMailBuilder(template_mail_cls=InlineCSSTemplateMail)
    email = mail_instance.contact_us_email(
        "wikipedialibrary@wikimedia.org",
        {"editor_wp_username": editor_wp_username, "body": body},
    )
    email.extra_headers["Reply-To"] = ", ".join(reply_to)
    if kwargs["cc"]:
        cc.append(user_email)
        email.extra_headers["Cc"] = ", ".join(cc)

    logger.info("Email constructed.")
    email.send()
    logger.info("Email queued.")
