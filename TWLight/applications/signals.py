import django.dispatch

from django_comments.signals import comment_was_posted

from .models import Application

class Reminder(object):
    coordinator_reminder = django.dispatch.Signal(providing_args=['app_status', 'app_count', 'coordinator_wp_username', 'coordinator_email', 'coordinator_lang'])

@django.dispatch.receiver(comment_was_posted)
def under_discussion(sender, comment, request, **kwargs):
    """
    When users send a comment on an application which currently has the
    PENDING status, automatically set it to 'Under discussion' (QUESTION).
    """
    application_object = Application.objects.get(pk=comment.object_pk)

    if application_object.status == Application.PENDING:
        application_object.status = Application.QUESTION
        application_object.save()