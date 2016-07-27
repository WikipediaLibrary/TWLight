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
from urlparse import urljoin

from django.contrib.comments.models import Comment
from django.contrib.comments.signals import comment_was_posted
from django.contrib.sites.models import get_current_site
from django.dispatch import receiver

from TWLight.applications.models import Application


logger = logging.getLogger(__name__)


# COMMENT NOTIFICATION
# ------------------------------------------------------------------------------


class CommentNotificationEmailEditors(template_mail.TemplateMail):
    name = 'comment_notification_editors'


class CommentNotificationEmailOthers(template_mail.TemplateMail):
    name = 'comment_notification_others'


@receiver(comment_was_posted)
def send_comment_notification_emails(sender, **kwargs):
    """
    Any time a comment is posted on an application, this sends email to the
    application owner and anyone else who previously commented.
    """
    # This import must go here. We cannot import ContentType too early in the
    # Django startup process, but we have to import this file (or at least this
    # function) early enough that it can be connected as a signal receiver
    # (which we do in __init__.py). Importing ContentType at the top level would
    # therefore result in fail, and we delay it until now.
    from django.contrib.contenttypes.models import ContentType
    apptype = ContentType.objects.get(model='Application')

    current_comment = kwargs['comment']
    app = current_comment.content_object
    assert isinstance(app, Application)

    logger.info('Received comment signal on app number {app.pk}; preparing '
                'to send notification emails'.format(app=app))

    if 'request' in kwargs:
        # This is the expected case; the comment_was_posted signal should send
        # this.
        request = kwargs['request']
        base_url = get_current_site(request).domain
        app_url = urljoin(base_url, app.get_absolute_url())
    else:
        # Hopefully adequate default (only has path, not base URL)
        app_url = app.get_absolute_url()

    # If the editor who owns this application was not the comment poster, notify
    # them of the new comment.
    if current_comment.user_email != app.editor.user.email:
        email = CommentNotificationEmailEditors()
        email.send(app.editor.user.email, {'app': app, 'app_url': app_url})
        logger.info('Email queued for {app.editor.user.email} about app #{app.pk}'.format(
            app=app))

    # Send to any previous commenters on the thread, other than the editor and
    # the person who left the comment just now.
    all_comments = Comment.objects.filter(object_pk=app.pk, content_type=apptype)
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
        email = CommentNotificationEmailOthers()
        email.send(user_email, {'app': app, 'app_url': app_url})
        logger.info('Email queued for {app.editor.user.email} about app #{app.pk}'.format(
            app=app))

