"""
A set of tokens (key/secret pairs) used to identify actors during and after
an OAuth handshake.
"""
from collections import namedtuple

ConsumerToken = namedtuple("ConsumerToken", ['key', 'secret'])
"""
Represents a consumer (you).  This key/secrets pair is provided by MediaWiki
when you register an OAuth consumer (see
``Special:OAuthConsumerRegistration``). Note that Extension:OAuth must be
installed in order in order for ``Special:OAuthConsumerRegistration`` to
appear.

:Parameters:
    key : `str`
        A hex string identifying the user
    secret : `str`
        A hex string used to sign communications
"""

RequestToken = namedtuple("RequestToken", ['key', 'secret'])
"""
Represents a request for access during authorization.  This key/secret pair
is provided by MediaWiki via ``Special:OAuth/initiate``.
Once the user authorize you, this token can be traded for an `AccessToken`
via `complete()`.

:Parameters:
    key : `str`
        A hex string identifying the user
    secret : `str`
        A hex string used to sign communications
"""

AccessToken = namedtuple("AccessToken", ['key', 'secret'])
"""
Represents an authorized user.  This key and secret is provided by MediaWiki
via ``Special:OAuth/complete`` and later used to show MediaWiki evidence of
authorization.

:Parameters:
    key : `str`
        A hex string identifying the user
    secret : `str`
        A hex string used to sign communications
"""
