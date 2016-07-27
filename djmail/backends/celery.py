# -*- encoding: utf-8 -*-

from __future__ import absolute_import

from django.conf import settings

from . import base
from .. import tasks
from .. import utils


class EmailBackend(base.BaseEmailBackend):
    """
    Asynchronous email back-end that uses
    Celery task for sending emails.
    """
    def send_messages(self, email_messages):
        if len(email_messages) == 0:
            return 0

        if settings.CELERY_TASK_SERIALIZER in ('json', ):
            email_messages = [utils.serialize_email_message(e) for e in email_messages]
        return tasks.send_messages.delay(email_messages)
