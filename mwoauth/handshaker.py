"""
A client for managing an OAuth handshake with MediaWiki.

:Example:
    .. code-block:: python

        from mwoauth import ConsumerToken, Handshaker
        from six.moves import input # For compatibility between python 2 and 3

        # Consruct a "consumer" from the key/secret provided by MediaWiki
        import config
        consumer_token = ConsumerToken(
            config.consumer_key, config.consumer_secret)

        # Construct handshaker with wiki URI and consumer
        handshaker = Handshaker(
            "https://en.wikipedia.org/w/index.php", consumer_token)

        # Step 1: Initialize -- ask MediaWiki for a temporary key/secret for
        # user
        redirect, request_token = handshaker.initiate()

        # Step 2: Authorize -- send user to MediaWiki to confirm authorization
        print("Point your browser to: %s" % redirect) #
        response_qs = input("Response query string: ")

        # Step 3: Complete -- obtain authorized key/secret for "resource owner"
        access_token = handshaker.complete(request_token, response_qs)
        print(str(access_token))

        # Step 4: Identify -- (optional) get identifying information about the
        # user
        identity = handshaker.identify(access_token)
        print("Identified as {username}.".format(**identity))
"""
from .functions import complete, identify, initiate


class Handshaker(object):
    """

    :Parameters:
        mw_uri : `str`
            The base URI of the wiki (provider) to authenticate with.  This uri
            should end in ``"index.php"``.
        consumer_token : :class:`~mwoauth.ConsumerToken`
            A token representing you, the consumer.  Provided by MediaWiki via
            ``Special:OAuthConsumerRegistration``.
    """

    def __init__(self, mw_uri, consumer_token):
        self.mw_uri = mw_uri
        self.consumer_token = consumer_token

    def initiate(self, callback='oob'):
        """
        Initiates an OAuth handshake with MediaWiki.

        :Parameters:
            callback : `str`
                Callback URL. Defaults to 'oob'.

        :Returns:
            A `tuple` of two values:

            * a MediaWiki URL to direct the user to
            * a :class:`~mwoauth.RequestToken` representing an access request


        """
        return initiate(self.mw_uri, self.consumer_token, callback=callback)

    def complete(self, request_token, response_qs):
        """
        Completes an OAuth handshake with MediaWiki by exchanging an

        :Parameters:
            request_token : `RequestToken`
                A temporary token representing the user.  Returned by
                `initiate()`.
            response_qs : `bytes`
                The query string of the URL that MediaWiki forwards the user
                back after authorization.

        :Returns:
            An :class:`~mwoauth.AccessToken` containing an authorized
            key/secret pair that can be stored and used by you.
        """
        return complete(
            self.mw_uri, self.consumer_token, request_token, response_qs)

    def identify(self, access_token, leeway=10.0):
        """
        Gather's identifying information about a user via an authorized token.

        :Parameters:
            access_token : `AccessToken`
                A token representing an authorized user.  Obtained from
                `complete()`.
            leeway : `int` | `float`
                The number of seconds of leeway to account for when examining a
                tokens "issued at" timestamp.

        :Returns:
            A dictionary containing identity information.
        """
        return identify(self.mw_uri, self.consumer_token, access_token,
                        leeway=leeway)
