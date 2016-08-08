import logging
from mwoauth import ConsumerToken, Handshaker, AccessToken

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.utils.translation import ugettext as _

from .helpers.wiki_list import WIKI_DICT
from .forms import HomeWikiForm
from .models import Editor

logger = logging.getLogger(__name__)

# Construct a "consumer" from the key/secret provided by MediaWiki.
consumer_token = ConsumerToken(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)

# We can't construct the handshaker now, because its base URL will vary
# depending on the user's home wiki. We will add handshakers to this as needed.
# Keys will be base URLs; values will be handshaker objects.
handshakers = {}

def dehydrate_token(token):
    """
    Convert the request token into a dict suitable for storing in the session.
    """
    session_token = {}
    session_token['key'] = token.key
    session_token['secret'] = token.secret
    return session_token


def rehydrate_token(token):
    """
    Convert the stored dict back into a request token that we can use for
    getting an access grant.
    """
    request_token = ConsumerToken(token['key'], token['secret'])
    return request_token


class OAuthBackend(object):

    def _create_user_and_editor(self, identity):
        logger.info('creating user')

        # -------------------------- Create the user ---------------------------
        email = identity['email']
        username = identity['sub']

        # Since we are not providing a password argument, this will call
        # set_unusable_password, which is exactly what we want; users created
        # via OAuth should only be allowed to log in via OAuth.
        user = User.objects.create_user(username=username, email=email)

        # ------------------------- Create the editor --------------------------
        editor = Editor()

        editor.user = user
        editor.wp_sub = identity['sub']
        editor.update_from_wikipedia(identity) # This call also saves the editor

        return user, editor


    def _get_and_update_user_from_identity(self, identity):
        """
        If we have an Editor matching the identity returned by Wikipedia,
        update it with the identity parameters and return its associated user.
        If we don't, create an Editor and User, and return that user.

        If the wikipedia account does not meet our eligibility criteria, create
        a TWLight account if needed, but set it as inactive. Also deactivate
        any existing accounts that have become ineligible.

        Also return a boolean that is True if we created a user during this
        call and False if we did not.
        """
        logger.info('getting user')
        try:
            editor = Editor.objects.get(wp_sub=identity['sub'])
            user = editor.user
            created = False
            editor.update_from_wikipedia(identity)

        except Editor.DoesNotExist:
            user, editor = self._create_user_and_editor(identity)
            created = True

        return user, created


    def authenticate(self, request=None, access_token=None, handshaker=None):
        if not request or not access_token or not handshaker:
            # You must have meant to use a different authentication backend.
            # Returning None will make Django keep going down its list of
            # options.
            return None

        try:
            assert isinstance(access_token, AccessToken)
        except AssertionError:
            return None

        # Get identifying information about the user. This doubles as a way
        # to authenticate the access token, which only Wikimedia can do,
        # and thereby to authenticate the user (which is hard for us to do as
        # we have no password.)
        try:
            identity = handshaker.identify(access_token)
        except:
            logger.warning('Someone tried to log in but presented an invalid '
                'access token')
            raise PermissionDenied

        logger.info('identity was %s', identity)

        # Get or create the user.
        user, created = self._get_and_update_user_from_identity(identity)
        request.session['user_created'] = created

        # The authenticate() function of a Django auth backend must return
        # the user.
        return user


    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None



class OAuthInitializeView(FormView):
    """
    Ask Wikipedia for a temporary key/secret for the user, and redirect
    them to their home Wikipedia to confirm authorization.
    """
    template_name = 'users/oauth_login.html'
    form_class = HomeWikiForm

    def form_valid(self, form):
        # The form returns the code for the home wiki (the first element of the
        # tuple in WIKIS), but we want the URL, so we grab it from WIKI_DICT.
        home_wiki = WIKI_DICT[form.cleaned_data['home_wiki']]
        base_url = 'https://{home_wiki}/w/index.php'.format(home_wiki=home_wiki)

        try:
            # Get handshaker matching this base URL from our dict.
            handshaker = handshakers[base_url]
        except KeyError:
            # Whoops, it doesn't exist. Initialize a handshaker and store it
            # for later.
            handshaker = Handshaker(base_url, consumer_token)
            handshakers[base_url] = handshaker

        redirect, request_token = handshaker.initiate()
        self.request.session['request_token'] = dehydrate_token(request_token)
        self.request.session['base_url'] = base_url
        # TODO where is the proper, secure place to store this?
        logger.info('request token was %s', request_token)
        return HttpResponseRedirect(redirect)



class OAuthCallbackView(View):
    """
    Receive the redirect from Wikipedia and parse the response token.
    """

    def get(self, request, *args, **kwargs):
        response_qs = request.META['QUERY_STRING']

        # Get the handshaker. It should have already been constructed by
        # OAuthInitializeView.
        base_url = request.session.pop('base_url'), None
        try:
            handshaker = handshakers[base_url]
        except KeyError:
            logger.exception('Could not find handshaker')
            raise PermissionDenied

        # Get the request token, placed in session by OAuthInitializeView.
        session_token = request.session.pop('request_token', None)
        request_token = rehydrate_token(session_token)

        logger.info('request token was %s', request_token)
        if not request_token:
            logger.info('no request token :(')
            raise PermissionDenied

        # See if we can complete the OAuth process.
        try:
            access_token = handshaker.complete(request_token, response_qs)
        except:
            logger.exception('Access token generation failed :(')
            raise PermissionDenied

        user = authenticate(request=request,
                            access_token=access_token,
                            handshaker=handshaker)
        created = request.session.pop('user_created', False)

        if not user.is_active:
            # Do NOT log in the user.

            if created:
                messages.add_message(request, messages.WARNING,
                    _('Your Wikipedia account does not meet the eligibility '
                      'criteria in the terms of use, so your Wikipedia Library '
                      'Card Platform account cannot be activated.'))
            else:
                messages.add_message(request, messages.WARNING,
                    _('Either your Wikipedia Library Card Platform account has '
                      'been deactivated or your Wikipedia account no longer '
                      'meets the eligibility criteria in the terms of use, so '
                      'you cannot be logged in.'))

            url = reverse_lazy('terms')

        else:
            login(request, user)

            if created:
                # Translators: this message is displayed to users with brand new accounts.
                messages.add_message(request, messages.INFO, _('Welcome! Please '
                    'agree to the terms of use.'))
                url = reverse_lazy('terms')
            else:
                messages.add_message(request, messages.INFO, _('Welcome back!'))
                url = reverse_lazy('users:editor_detail',
                    kwargs={'pk': user.editor.pk})

        return HttpResponseRedirect(url)
