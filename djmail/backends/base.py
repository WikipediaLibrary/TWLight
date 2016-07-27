# -*- encoding: utf-8 -*-

from __future__ import unicode_literals


class BaseEmailBackend(object):
    """
    Base class that implements a Django
    mail back-end interface.
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        raise NotImplementedError
