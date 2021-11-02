from django.contrib.messages.storage.session import SessionStorage
from django.contrib.messages.storage.base import Message
from .view_mixins import DedupMessageMixin


class SessionDedupStorage(DedupMessageMixin, SessionStorage):
    """
    Custom session storage to prevent storing duplicate messages.
    cribbed directly from: https://stackoverflow.com/a/25157660
    """

    pass
