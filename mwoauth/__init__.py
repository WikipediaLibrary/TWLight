"""Provides a collection of utilities for easily working with MediaWiki's
OAuth1.0a implementation."""
from .handshaker import Handshaker
from .tokens import AccessToken, ConsumerToken, RequestToken
from .functions import initiate, complete, identify
