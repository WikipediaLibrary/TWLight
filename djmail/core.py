# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import io
import logging
import sys
import traceback

from django.conf import settings
from django.core.mail import get_connection
from django.core.paginator import Paginator
from django.utils import timezone
StringIO = io.BytesIO if sys.version_info[0] == 2 else io.StringIO

from . import models

logger = logging.getLogger(__name__)


def _chunked_iterate_queryset(queryset, chunk_size=10):
    """
    Given a queryset, use a paginator for iterating over the queryset
    but obtaining from database delimited set of result parametrized
    with `chunk_size` parameter.
    """
    paginator = Paginator(queryset, chunk_size)
    for page_index in paginator.page_range:
        page = paginator.page(page_index)
        for item in page.object_list:
            yield item


def _safe_send_message(message_model, connection):
    """
    Given a message model, try to send it, if it fails,
    increment retry count and save stack trace in
    message model.
    """
    email = message_model.get_email_message()
    sended = 0

    with StringIO() as f:
        try:
            sended = connection.send_messages([email])
        except Exception:
            traceback.print_exc(file=f)
            f.seek(0)
            message_model.exception = f.read()
            logger.error(message_model.exception)
        else:
            if sended == 1:
                message_model.status = models.STATUS_SENT
                message_model.sent_at = timezone.now()
            else:
                message_model.status = models.STATUS_FAILED
                message_model.retry_count += 1

        message_model.save()
        return sended


def _get_real_backend():
    real_backend_path = getattr(
        settings,
        'DJMAIL_REAL_BACKEND',
        'django.core.mail.backends.console.EmailBackend')
    return get_connection(backend=real_backend_path, fail_silently=False)


def _send_messages(email_messages):
    connection = _get_real_backend()

    # Create a messages on a database for correct
    # tracking of their status.
    email_models = [models.Message.from_email_message(email, save=True)
                    for email in email_messages]

    # Open connection for send all messages
    connection.open()
    try:
        sended_counter = 0
        for email, model_instance in zip(email_messages, email_models):
            if hasattr(email, "priority"):
                if email.priority <= models.PRIORITY_LOW:
                    model_instance.priority = email.priority
                    model_instance.status = models.STATUS_PENDING
                    model_instance.save()
                    sended_counter += 1
                    continue

            sended_counter += _safe_send_message(model_instance, connection)
    finally:
        connection.close()
    return sended_counter


def _send_pending_messages():
    """
    Send pending, low priority messages.
    """
    queryset = models.Message.objects.filter(status=models.STATUS_PENDING)\
                                     .order_by('-priority', 'created_at')
    connection = _get_real_backend()
    connection.open()
    try:
        sended_counter = 0
        for message_model in _chunked_iterate_queryset(queryset, 100):
            # Use one unique connection for sending all messages
            sended_counter += _safe_send_message(message_model, connection)
    finally:
        connection.close()
    return sended_counter


def _retry_send_messages():
    """
    Retry to send failed messages.
    """
    max_retry_value = getattr(settings, 'DJMAIL_MAX_RETRY_NUMBER', 3)
    queryset = models.Message.objects.filter(status=models.STATUS_FAILED)\
                                     .filter(retry_count__lte=max_retry_value)\
                                     .order_by('-priority', 'created_at')

    connection = _get_real_backend()
    connection.open()
    try:
        sended_counter = 0
        for message_model in _chunked_iterate_queryset(queryset, 100):
            sended_counter += _safe_send_message(message_model, connection)
    finally:
        connection.close()
    return sended_counter


def _mark_discarded_messages():
    """
    Search messages exceeding the global retry
    limit and marks them as discarded.
    """
    max_retry_value = getattr(settings, 'DJMAIL_MAX_RETRY_NUMBER', 3)
    queryset = models.Message.objects.filter(status=models.STATUS_FAILED,
                                             retry_count__gt=max_retry_value)
    return queryset.update(status=models.STATUS_DISCARDED)
