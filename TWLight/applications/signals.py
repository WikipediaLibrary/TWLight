import logging

from django.dispatch import receiver, Signal

from django_comments.signals import comment_was_posted

from TWLight.resources.models import Partner

from .models import Application

no_more_accounts = Signal(providing_args=['partner_pk'])

logger = logging.getLogger(__name__)

class Reminder(object):
    coordinator_reminder = Signal(providing_args=['app_status', 'app_count', 'coordinator_wp_username', 'coordinator_email', 'coordinator_lang'])

@receiver(comment_was_posted)
def under_discussion(sender, comment, request, **kwargs):
    """
    When coordinators post a comment on an application which currently has the
    PENDING status, automatically set it to 'Under discussion' (QUESTION).
    """
    application_object = Application.objects.get(pk=comment.object_pk)

    if application_object.status == Application.PENDING and application_object.editor.user.username != request.user.username:
        application_object.status = Application.QUESTION
        application_object.save()


@receiver(no_more_accounts)
def set_partner_status(sender, **kwargs):
    """
    Whenever an application is approved (except for in BatchEditView)
    we do some calculations to see if we've run out of accounts. If 
    we have, we mark the partner as waitlisted, if not continue.
    """
    partner_pk = kwargs['partner_pk']
    try:
        partner = Partner.objects.get(pk=partner_pk)
        partner.status = Partner.WAITLIST
        partner.save()
    except Partner.DoesNotExist:
        logger.info('set_partner_status signal received, but'
            ' partner {pk} does not exist – unable to set'
            ' partner status'.format(pk=partner_pk))
            