# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from celery.task import task

from . import core
from . import utils


@task(name='tasks.send_messages')
def send_messages(messages):
    """
    Celery standard task for sending messages asynchronously.
    """
    return core._send_messages([
        utils.deserialize_email_message(m)
        if isinstance(m, utils.string_types) else m
        for m in messages
    ])


@task(name='tasks.retry_send_messages')
def retry_send_messages():
    """
    Celery periodic task retrying to send failed messages.
    """
    core._send_pending_messages()
    core._mark_discarded_messages()
    core._retry_send_messages()
