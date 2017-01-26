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
from django.db.models.signals import pre_save
from django.dispatch import receiver

from TWLight.applications.models import Application


logger = logging.getLogger(__name__)


# COMMENT NOTIFICATION
# ------------------------------------------------------------------------------


class CommentNotificationEmailEditors(template_mail.TemplateMail):
    name = 'comment_notification_editors'



class CommentNotificationEmailOthers(template_mail.TemplateMail):
    name = 'comment_notification_others'



class ApprovalNotification(template_mail.TemplateMail):
    name = 'approval_notification'



class RejectionNotification(template_mail.TemplateMail):
    name = 'rejection_notification'



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
            email.send(app.editor.user.email, {'app': app, 'app_url': app_url})
            logger.info('Email queued for {app.editor.user.email} about '
                'app #{app.pk}'.format(app=app))

    # Send to any previous commenters on the thread, other than the editor and
    # the person who left the comment just now.
    all_comments = Comment.objects.filter(object_pk=app.pk,
                        content_type__model='application',
                        content_type__app_label='applications')
    user_emails = set(
        [comment.user.email for comment in all_comments]
        )

    user_emails.remove(current_comment.user_email)
    try:
        user_emails.remove(app.editor.user.email)
    except KeyError:
        # If the editor is not among the prior commenters, that's fine; no
        # reason they should be.
        pass

    for user_email in user_emails:
        if user_email:
            email = CommentNotificationEmailOthers()
            email.send(user_email, {'app': app, 'app_url': app_url})
            logger.info('Email queued for {app.editor.user.email} about app '
                '#{app.pk}'.format(app=app))



def send_approval_notification_email(instance):
    email = ApprovalNotification()
    email.send(instance.user.email,
        {'user': instance.user, 'partner': instance.partner})


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
        {'user': instance.user,
         'partner': instance.partner,
         'app_url': app_url})


@receiver(pre_save, sender=Application)
def update_app_status_on_save(sender, instance, **kwargs):
    """
    If the Application's status has changed in a way that justifies sending
    email, do so. Otherwise, do nothing.
    """
    # Maps application status to the correct email handling function.
    handlers = {
        Application.APPROVED: send_approval_notification_email,
        Application.NOT_APPROVED: send_rejection_notification_email,
    }

    # Case 1: Application already existed; status has been changed.
    if instance.id:
        orig_app = Application.objects.get(pk=instance.id)
        orig_status = orig_app.status

        if orig_status != instance.status:
            try_send = True
        else:
            try_send = False

    # Case 2: Application was just created.
    else:
        try_send = True

    if try_send:
        try:
            # Send email if it has an email-worthy status.
            handlers[instance.status](instance)
        except KeyError:
            # Or do nothing if the status is uninteresting.
            pass
