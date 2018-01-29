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
2) They can use {% trans %} and {% blocktrans %}. In fact, they _should_, to
   support internationalization.

Add a 'lang' attribute to the context passed into TemplateMail in order to
specify which language to render the template in.

There is no need to faff about with Celery in this file. djmail will decide
whether to send synchronously or asynchronously based on the value of
settings.DJMAIL_REAL_BACKEND.
"""
from djmail import template_mail
import logging

from django_comments.models import Comment
from django_comments.signals import comment_was_posted
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse_lazy
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404


from TWLight.applications.models import Application
from TWLight.applications.signals import Reminder
from TWLight.resources.models import Partner


logger = logging.getLogger(__name__)


# COMMENT NOTIFICATION
# ------------------------------------------------------------------------------


class CommentNotificationEmailEditors(template_mail.TemplateMail):
    name = 'comment_notification_editors'


class CommentNotificationEmailOthers(template_mail.TemplateMail):
    name = 'comment_notification_others'


class ApprovalNotification(template_mail.TemplateMail):
    name = 'approval_notification'


class WaitlistNotification(template_mail.TemplateMail):
    name = 'waitlist_notification'


class RejectionNotification(template_mail.TemplateMail):
    name = 'rejection_notification'


class CoordinatorReminderNotification(template_mail.TemplateMail):
    name = 'coordinator_reminder_notification'


@receiver(Reminder.coordinator_reminder)
def send_coordinator_reminder_emails(sender, **kwargs):
    """
    Any time the related managment command is run, this sends email to the
    to designated coordinators, reminding them to login
    to the site if there are pending applications.
    """
    app_status = kwargs['app_status']
    app_count = kwargs['app_count']
    coordinator_wp_username = kwargs['coordinator_wp_username']
    coordinator_email = kwargs['coordinator_email']
    coordinator_lang = kwargs['coordinator_lang']
    base_url = get_current_site(None).domain
    path = reverse_lazy('applications:list')
    link = 'https://{base}{path}'.format(base=base_url, path=path)

    logger.info(u'Received coordinator reminder signal for {coordinator_wp_username}; '
        'preparing to send reminder email to {coordinator_email}.'.format(coordinator_wp_username=coordinator_wp_username, coordinator_email=coordinator_email))
    email = CoordinatorReminderNotification()
    logger.info('Email constructed.')
    email.send(coordinator_email,
        {'user': coordinator_wp_username,
         'lang': coordinator_lang,
         'app_status': app_status,
         'app_count': app_count,
         'link': link})
    logger.info(u'Email queued.')

@receiver(comment_was_posted)
def send_comment_notification_emails(sender, **kwargs):
    """
    Any time a comment is posted on an application, this sends email to the
    application owner and anyone else who previously commented.
    """
    current_comment = kwargs['comment']
    app = current_comment.content_object
    assert isinstance(app, Application)

    logger.info('Received comment signal on app number {app.pk}; preparing '
                'to send notification emails'.format(app=app))

    if 'request' in kwargs:
        # This is the expected case; the comment_was_posted signal should send
        # this.
        request = kwargs['request']
    else:
        # But if there's no request somehow, get_current_site has a sensible
        # default.
        request = None

    base_url = get_current_site(request).domain
    logger.info('Site base_url is {base_url}'.format(base_url=base_url))
    app_url = 'https://{base}{path}'.format(
        base=base_url, path=app.get_absolute_url())
    logger.info('app_url is {app_url}'.format(app_url=app_url))

    # If the editor who owns this application was not the comment poster, notify
    # them of the new comment.
    if current_comment.user_email != app.editor.user.email:
        if app.editor.user.email:
            logger.info('we should notify the editor')
            email = CommentNotificationEmailEditors()
            logger.info('email constructed')
            email.send(app.editor.user.email,
                {'user': app.editor.wp_username,
                 'lang': app.editor.user.userprofile.lang,
                 'app': app,
                 'app_url': app_url})
            logger.info('Email queued for {app.editor.user.email} about '
                'app #{app.pk}'.format(app=app))

    # Send to any previous commenters on the thread, other than the editor and
    # the person who left the comment just now.
    all_comments = Comment.objects.filter(object_pk=app.pk,
                        content_type__model='application',
                        content_type__app_label='applications')
    users = set(
        [comment.user for comment in all_comments]
        )

    users.remove(current_comment.user)
    try:
        users.remove(app.editor.user)
    except KeyError:
        # If the editor is not among the prior commenters, that's fine; no
        # reason they should be.
        pass

    for user in users:
        if user:
            email = CommentNotificationEmailOthers()
            email.send(user.email,
                {'user': user.editor.wp_username,
                 'lang': user.userprofile.lang,
                 'app': app,
                 'app_url': app_url})
            logger.info('Email queued for {app.editor.user.email} about app '
                '#{app.pk}'.format(app=app))


def send_approval_notification_email(instance):
    email = ApprovalNotification()
    email.send(instance.user.email,
        {'user': instance.user.editor.wp_username,
         'lang': instance.user.userprofile.lang,
         'partner': instance.partner})


def send_waitlist_notification_email(instance):
    base_url = get_current_site(None).domain
    path = reverse_lazy('partners:list')
    link = 'https://{base}{path}'.format(base=base_url, path=path)

    email = WaitlistNotification()
    email.send(instance.user.email,
        {'user': instance.user.editor.wp_username,
         'lang': instance.user.userprofile.lang,
         'partner': instance.partner,
         'link': link})


def send_rejection_notification_email(instance):
    base_url = get_current_site(None).domain

    if instance.pk:
        app_url = 'https://{base}{path}'.format(
            base=base_url, path=instance.get_absolute_url())
    else:
        # If we are sending an email for a newly created instance, it won't have
        # a pk, so instance.get_absolute_url() won't return successfully.
        # This should lead to an imperfect but navigable user experience, given
        # the text of the email - it won't take them straight to their app, but
        # it will take them to a page *via which* they can perform the review
        # steps described in the email template.
        app_url = reverse_lazy('users:home')

    email = RejectionNotification()
    email.send(instance.user.email,
        {'user': instance.user.editor.wp_username,
         'lang': instance.user.userprofile.lang,
         'partner': instance.partner,
         'app_url': app_url})


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
        'waitlist': send_waitlist_notification_email,
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
        # SENT is a post approval step that we don't need to send emails about.

        if instance.partner.status == Partner.WAITLIST:
            handler_key = 'waitlist'
        elif instance.status == Application.SENT:
            handler_key = None
        else:
            handler_key = instance.status

    if handler_key:
        try:
            # Send email if it has an email-worthy status.
            handlers[handler_key](instance)
        except KeyError:
            # This is probably okay - it probably means we were in case 2 above
            # and the application was created with PENDING status. We'll only
            # log the surprising cases.
            if handler_key != Application.PENDING:
                logger.exception('Email handler key was set to {handler_key}, '
                    'but no such handler exists'.format(handler_key=handler_key))
            pass


@receiver(pre_save, sender=Partner)
def notify_applicants_when_waitlisted(sender, instance, **kwargs):
    """
    When Partners are switched to WAITLIST status, anyone with open applications
    should be notified.
    """
    if instance.id:
        orig_partner = get_object_or_404(Partner, pk=instance.id)

        if ((orig_partner.status != instance.status) and 
            instance.status == Partner.WAITLIST):

            for app in orig_partner.applications.filter(
                status__in=[Application.PENDING, Application.QUESTION]):
                send_waitlist_notification_email(app)
