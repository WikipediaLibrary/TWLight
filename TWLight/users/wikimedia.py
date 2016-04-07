"""
Adds a backend for Wikimedia OAuth suitable for plugging into
python-social-auth.

See https://www.mediawiki.org/wiki/OAuth/For_Developers and 
https://tools.wmflabs.org/oauth-hello-world/ .
"""
from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse
from xml.dom import minidom

from social.backends.oauth import BaseOAuth1

from django.conf import settings

BASE_URL = "https://en.wikipedia.org/w/index.php"
PARAMS = {
    'initiate': {'title': "Special:OAuth/initiate"},
    'request_token': {'title': "Special:OAuth/authorize"},
    'access_token': {'title': "Special:OAuth/token"},
    'identify': {'title': "Special:OAuth/identify"}
}

class WikimediaOAuth(BaseOAuth1):
    """Wikimedia OAuth authentication backend"""
    name = 'wikimedia'
    AUTHORIZATION_URL = _update_with_params(BASE_URL, PARAMS['initiate'])
    REQUEST_TOKEN_URL = _update_with_params(BASE_URL, PARAMS['request_token'])
    ACCESS_TOKEN_URL = _update_with_params(BASE_URL, PARAMS['access_token'])
    IDENTIFY_URL = _update_with_params(BASE_URL, PARAMS['identify'])


    def _update_with_params(self, base_url, params):
        parsed_url = urlparse(base_url)
        base_params = parse_qs(parsed_url.params)
        base_params.update(params)
        new_qs = urlencode(base_params)
        url = urlunparse(parsed_url._replace(params=new_qs))
        return url


    def get_user_details(self, response):
        """Return user details from Wikimedia account"""
        return {
            'username': response['username'],       # wikipedia username
            'sub': response['sub'],                 # wp account ID
            'rights': response['rights'],           # user rights on-wiki
            'editcount': response['editcount'],
            'email': response['email'],
            # Date registered: YYYYMMDDHHMMSS
            'registered': response['registered']
            # We could attempt to harvest real name, but we won't; we'll let
            # users enter it if required by partners, and avoid knowing the
            # data otherwise.
        }

    def user_data(self, access_token, *args, **kwargs):
        """Return user data provided"""
        response = self.oauth_request(
            access_token, self.IDENTIFY_URL
        )
        try:
            dom = minidom.parseString(response.content)
        except ValueError:
            return None
        user = dom.getElementsByTagName('user')[0]
        try:
            avatar = dom.getElementsByTagName('img')[0].getAttribute('href')
        except IndexError:
            avatar = None
        return {
            'id': user.getAttribute('id'),
            'username': user.getAttribute('display_name'),
            'account_created': user.getAttribute('account_created'),
            'avatar': avatar
        }