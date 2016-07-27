# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import base64
import pickle

try:
    # Django >= 1.4.5
    from django.utils.encoding import force_bytes
    from django.utils.encoding import force_text
except ImportError:
    # Django < 1.4.5
    from django.utils.encoding import smart_bytes as force_bytes
    from django.utils.encoding import smart_unicode as force_text

from django.utils.six import string_types


__all__ = (
    'force_bytes',
    'force_text',
    'string_types',
    'deserialize_email_message',
    'serialize_email_message'
)


def deserialize_email_message(data):
    return pickle.loads(base64.b64decode(force_bytes(data)))


def serialize_email_message(email_message):
    return force_text(base64.b64encode(pickle.dumps(email_message)))


