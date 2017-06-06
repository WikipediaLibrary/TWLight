import logging
from mwoauth import ConsumerToken, Handshaker, AccessToken
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, DisallowedHost
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.utils.translation import ugettext as _

from .helpers.wiki_list import WIKI_DICT
from .forms import HomeWikiForm
from .models import Editor

logger = logging.getLogger(__name__)

try:
    ALLOWED_DOMAINS = settings.WP_CREDENTIALS.keys()
    # Construct a "consumer" from the key/secret provided by MediaWiki for all
    # available site domains. (Each domain requires a different set of
    # credentials.)
    CONSUMER_TOKENS = {domain: ConsumerToken(creds['key'], creds['secret'])
                       for domain, creds in settings.WP_CREDENTIALS.items()}
except AttributeError:
    # We'll get an AttributeError if the settings don't contain WP_CREDENTIALS.
    # This is the expected behavior for systems that don't have Wikipedia
    # OAuth credentials, like localhost. The system should not crash in that
    # case - it just shouldn't generate any tokens.
    ALLOWED_DOMAINS = []
    CONSUMER_TOKENS = {}

# Must be before handshaker construction
def _get_full_wiki_url(home_wiki):
    """
    Given something like 'en.wikipedia.org', return something like
    'https://en.wikipedia.org/w/index.php'.
    """
    return 'https://meta.wikimedia.org/w/index.php'


# Construct all conceivably needed handshakers. Will result in a dict like
# {domain: {wiki url: handshaker}}.
HANDSHAKERS = {}

WIKI_DOMAINS = WIKI_DICT.values()

for allowed_domain in ALLOWED_DOMAINS:
    tempdict = {}
    for wiki in WIKI_DOMAINS:
        tempdict[wiki] = Handshaker(
            _get_full_wiki_url(wiki), CONSUMER_TOKENS[allowed_domain])
    HANDSHAKERS[allowed_domain] = tempdict


def _get_token(domain):
    try:
        assert domain in ALLOWED_DOMAINS
    except AssertionError:
        logger.exception('Attempted to get a token for an unsupported domain')
        raise

    return CONSUMER_TOKENS[domain]


def _get_handshaker(domain, home_wiki):
    try:
        assert domain in ALLOWED_DOMAINS
    except AssertionError:
        logger.exception('Attempted to get a handshaker for an unsupported TWL domain')
        raise

    try:
        assert home_wiki in WIKI_DOMAINS
    except AssertionError:
        logger.exception('Attempted to get a handshaker for an unsupported wiki')
        raise

    return HANDSHAKERS[domain][home_wiki]


def _dehydrate_token(token):
    """
    Convert the request token into a dict suitable for storing in the session.
    """
    session_token = {}
    session_token['key'] = token.key
    session_token['secret'] = token.secret
    return session_token


def _rehydrate_token(token):
    """
    Convert the stored dict back into a request token that we can use for
    getting an access grant.
    """
    request_token = ConsumerToken(token['key'], token['secret'])
    return request_token


class OAuthBackend(object):

    def _get_language_code(self, identity):
        logger.info('Getting language code...')
        home_wiki_url = identity['iss']
        extractor = re.match(r'(https://)?(\w+).wikim|pedia.org', home_wiki_url)
        language_code = extractor.group(2)
        try:
            assert language_code in WIKI_DICT
        except AssertionError:
            logger.exception('Could not find code {lang} in WIKI_DICT; '
                'exiting'.format(lang=language_code))
            raise

        logger.info('Language code was {lang}.'.format(lang=language_code))

        return language_code


    def _get_username(self, identity):
        # The Wikipedia username is globally unique, but Wikipedia allows it to
        # have characters that the Django username system rejects. However,
        # wiki userID should be unique, and limited to ASCII.
        return '{sub}'.format(sub=identity['sub'])


    def _meets_minimum_requirement(self, identity):
        """
        This needs to be reworked to actually check against global_userinfo.
        """
        if 'autoconfirmed' in identity['rights']:
            return True

        return False


    def _create_user_and_editor(self, identity):
        # This can't be super informative because we don't want to log
        # identities.
        logger.info('Creating user.')

        #if not self._meets_minimum_requirement(identity):
            #This needs to be reworked to actually check against global_userinfo.
            #Don't create a User or Editor if this person does not meet the
            #minimum account quality requirement. It would be nice to provide
            #some user feedback here, but we can't; exception messages don't
            #get passed on as template context in Django 1.8. (They do in
            #1.10, so this can be revisited in future.)
            #logger.warning('User did not meet minimum requirements; not created.')
            #raise PermissionDenied


        # This will assert that the language code is a real Wikipedia, which
        # is good - we want to verify that assumption before proceeding.
        language_code = self._get_language_code(identity)

        # -------------------------- Create the user ---------------------------
        try:
            email = identity['email']
        except KeyError:
            email = None

        username = self._get_username(identity)

        # Since we are not providing a password argument, this will call
        # set_unusable_password, which is exactly what we want; users created
        # via OAuth should only be allowed to log in via OAuth.
        user = User.objects.create_user(username=username, email=email)

        # ------------------------- Create the editor --------------------------
        logger.info('Creating editor'.format(username=username))
        editor = Editor()

        editor.user = user

        editor.wp_sub = identity['sub']
        editor.home_wiki = language_code
        editor.update_from_wikipedia(identity) # This call also saves the editor

        logger.info('User and editor successfully created.')
        return user, editor


    def _get_and_update_user_from_identity(self, identity):
        """
        If we have an Editor and User matching the identity returned by
        Wikipedia, update the editor with the identity parameters and return its
        associated user. If we don't, create an Editor and User, and return that
        user.

        If the wikipedia account does not meet our eligibility criteria, create
        a TWLight account if needed, but set it as inactive. Also deactivate
        any existing accounts that have become ineligible.

        Also return a boolean that is True if we created a user during this
        call and False if we did not.
        """
        logger.info('Attempting to update editor after OAuth login.')
        try:
            username = self._get_username(identity)
            user = User.objects.get(username=username)

            # This login path should only be used for accounts created via
            # Wikipedia login, which all have editor objects.
            assert hasattr(user, 'editor')
            editor = user.editor

            editor.update_from_wikipedia(identity)
            logger.info('Editor {editor} updated.'.format(editor=editor))

            created = False

        except User.DoesNotExist:
            logger.info("Can't find user; creating one.")
            user, editor = self._create_user_and_editor(identity)
            created = True

        except AttributeError:
            logger.warning('A user tried using the Wikipedia OAuth '
                'login path but does not have an attached editor'.format(
                    username=identity['username']))
            raise

        logger.info('User and editor created/updated after OAuth login.')
        return user, created


    def authenticate(self, request=None, access_token=None, handshaker=None):
        logger.info('Authenticating user...')
        if not request or not access_token or not handshaker:
            logger.info('Missing OAuth authentication elements; falling back'
                'to another authentication method.')
            # You must have meant to use a different authentication backend.
            # Returning None will make Django keep going down its list of
            # options.
            return None

        try:
            assert isinstance(access_token, AccessToken)
        except AssertionError:
            logger.exception('Did not have a properly formed AccessToken')
            return None

        # Get identifying information about the user. This doubles as a way
        # to authenticate the access token, which only Wikimedia can do,
        # and thereby to authenticate the user (which is hard for us to do as
        # we have no password.)
        logger.info('Identifying user...')
        try:
            identity = handshaker.identify(access_token)
        except:
            logger.warning('Someone tried to log in but presented an invalid '
                'access token.')
            raise PermissionDenied

        # Get or create the user.
        logger.info('User has been identified; getting or creating user.')
        user, created = self._get_and_update_user_from_identity(identity)

        if created:
            home_wiki = re.search(r'(\w+).wikim|pedia.org',
                                 handshaker.mw_uri).group(1)

            try:
                # It's actually a wiki, right?
                assert home_wiki in WIKI_DICT
                user.editor.home_wiki = home_wiki
                user.editor.save()
            except AssertionError:
                # Site functionality mostly works if people don't
                # declare a homewiki. There are some broken bits, like the SUL
                # link, but users can set their homewiki, or admins can do it
                # in the admin interface.
                pass
        else:
            logger.info('User has been updated.'.format(user=user))

        request.session['user_created'] = created

        # The authenticate() function of a Django auth backend must return
        # the user.
        return user


    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.warning('There is no user {user_id}'.format(user_id=user_id))
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

        # The site might be running under multiple URLs, so find out the current
        # one (and make sure it's legit).
        # The Sites framework was designed for different URLs that correspond to
        # different databases or functionality - it's not a good fit here.
        try:
            domain = self.request.get_host()
            assert domain in settings.ALLOWED_HOSTS # safety first!
        except (AssertionError, DisallowedHost):
            logger.exception()
            raise PermissionDenied

        logger.info('home_wiki was {home_wiki}, domain was {domain}'.format(home_wiki=home_wiki, domain=domain))

        # Get handshaker matching this wiki URL from our dict.
        handshaker = _get_handshaker(domain, home_wiki)
        logger.info('handshaker gotten')

        try:
            redirect, request_token = handshaker.initiate()
        except:
            logger.exception('Handshaker not initiated')
            raise

        logger.info('handshaker initiated')
        self.request.session['request_token'] = _dehydrate_token(request_token)
        self.request.session['home_wiki'] = home_wiki
        return HttpResponseRedirect(redirect)



class OAuthCallbackView(View):
    """
    Receive the redirect from Wikipedia and parse the response token.
    """

    def get(self, request, *args, **kwargs):
        response_qs = request.META['QUERY_STRING']

        # Get the handshaker. It should have already been constructed by
        # OAuthInitializeView.
        try:
            domain = self.request.get_host()
            assert domain in settings.ALLOWED_HOSTS
        except (AssertionError, DisallowedHost):
            logger.exception()
            raise PermissionDenied

        home_wiki = request.session.pop('home_wiki', None)

        try:
            handshaker = _get_handshaker(domain, home_wiki)
        except AssertionError:
            # get_handshaker will throw AssertionErrors for invalid data.
            logger.exception('Could not find handshaker')
            raise PermissionDenied

        # Get the request token, placed in session by OAuthInitializeView.
        session_token = request.session.pop('request_token', None)
        request_token = _rehydrate_token(session_token)

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

            return_url = reverse_lazy('terms')

        else:
            login(request, user)

            if created:
                # Translators: this message is displayed to users with brand new accounts.
                messages.add_message(request, messages.INFO, _('Welcome! '
                    'Please agree to the terms of use.'))
                return_url = reverse_lazy('terms')
            else:
                messages.add_message(request, messages.INFO, _('Welcome back!'))
                return_url = reverse_lazy('users:editor_detail',
                    kwargs={'pk': user.editor.pk})

        return HttpResponseRedirect(return_url)
