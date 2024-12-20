import logging

from django.utils.http import url_has_allowed_host_and_scheme
from mwoauth import ConsumerToken, Handshaker, AccessToken
from mwoauth.errors import OAuthException
from sentry_sdk import capture_exception
import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.core.exceptions import DisallowedHost, PermissionDenied
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.http.request import QueryDict
from django.views.generic.base import View
from django.utils.safestring import mark_safe
from django.utils.translation import (
    get_language,
    gettext as _,
    activate as translation_activate,
)

from urllib.parse import urlencode

from .models import Editor, Session

logger = logging.getLogger(__name__)


def _localize_oauth_redirect(redirect):
    """
    Given an appropriate mediawiki oauth handshake url, return one that will
    present the user with a login page of their preferred language.
    """
    logger.info("Localizing oauth handshake URL.")

    redirect_parsed = urllib.parse.urlparse(redirect)
    redirect_query = urllib.parse.parse_qs(redirect_parsed.query)

    localized_redirect = redirect_parsed.scheme
    localized_redirect += "://"
    localized_redirect += redirect_parsed.netloc
    localized_redirect += redirect_parsed.path
    localized_redirect += "?title="
    localized_redirect += "Special:UserLogin"
    localized_redirect += "&uselang="
    localized_redirect += get_language()
    localized_redirect += "&returnto="
    localized_redirect += str(redirect_query["title"][0])
    localized_redirect += "&returntoquery="
    localized_redirect += "%26oauth_consumer_key%3D"
    localized_redirect += str(redirect_query["oauth_consumer_key"][0])
    localized_redirect += "%26oauth_token%3D"
    localized_redirect += str(redirect_query["oauth_token"][0])

    return localized_redirect


def _get_handshaker():
    consumer_token = ConsumerToken(
        settings.TWLIGHT_OAUTH_CONSUMER_KEY, settings.TWLIGHT_OAUTH_CONSUMER_SECRET
    )
    handshaker = Handshaker(settings.TWLIGHT_OAUTH_PROVIDER_URL, consumer_token)
    return handshaker


def _dehydrate_token(token):
    """
    Convert the request token into a dict suitable for storing in the session.
    """
    session_token = {}
    session_token["key"] = token.key
    session_token["secret"] = token.secret
    return session_token


def _rehydrate_token(token):
    """
    Convert the stored dict back into a request token that we can use for
    getting an access grant.
    """
    request_token = ConsumerToken(token["key"], token["secret"])
    return request_token


def _check_user_preferred_language(user):
    """
    Check if a user has a language preference set in their
    user profile
    ----------
    user : User
        User about to log into TWL

    Returns
    -------
    boolean
        Returns True if a user has a preferred language set and it doesn't
        match with the user's browser language
    """

    if user.userprofile.lang:
        # Check if the browser language is the same as the user's
        # preferred language
        browser_lang = get_language()
        user_lang = user.userprofile.lang
        if browser_lang != user_lang:
            return True
        else:
            return False
    else:
        return False


def _sanitize_next_url(next):
    if url_has_allowed_host_and_scheme(
        next[0],
        allowed_hosts=settings.ALLOWED_HOSTS,
        require_https=True,
    ):
        # Set the return url to the value of 'next'. Basic.
        return next[0]
    else:
        return None


class OAuthBackend(object):
    def _get_username(self, identity):
        # The Username is globally unique, but Wikipedia allows it to
        # have characters that the Django username system rejects. However,
        # wiki userID should be unique, and limited to ASCII.
        return "{sub}".format(sub=identity["sub"])

    def _create_user(self, identity):
        # This can't be super informative because we don't want to log
        # identities.
        logger.info("Creating user.")

        # -------------------------- Create the user ---------------------------
        try:
            email = identity["email"]
        except KeyError:
            email = None

        username = self._get_username(identity)

        # Since we are not providing a password argument, this will call
        # set_unusable_password, which is exactly what we want; users created
        # via OAuth should only be allowed to log in via OAuth.
        user = User.objects.create_user(username=username, email=email)
        logger.info("User user successfully created.")
        return user

    def _create_editor(self, user, identity):
        # ------------------------- Create the editor --------------------------
        logger.info("Creating editor.")
        editor = Editor()

        editor.user = user

        editor.wp_sub = identity["sub"]
        lang = get_language()
        editor.update_from_wikipedia(identity, lang)  # This call also saves the editor

        logger.info("Editor successfully created.")
        return editor

    def _create_user_and_editor(self, identity):
        user = self._create_user(identity)
        editor = self._create_editor(user, identity)
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
        logger.info("Attempting to update editor after OAuth login.")
        username = self._get_username(identity)
        user = User.objects.filter(username=username).first()
        if user is None:
            logger.info("Can't find user; creating one.")
            user, editor = self._create_user_and_editor(identity)
            return user, True
        should_update_lang = _check_user_preferred_language(user)
        if should_update_lang:
            user.userprofile.lang = get_language()
            user.userprofile.save()

        # This login path should only be used for accounts created via
        # Wikipedia login, which all have editor objects.
        if hasattr(user, "editor"):
            editor = user.editor

            lang = user.userprofile.lang
            editor.update_from_wikipedia(
                identity, lang
            )  # This call also saves the editor
            logger.info("Editor updated.")

            created = False
        else:
            try:
                logger.warning(
                    "A user tried using the Wikipedia OAuth "
                    "login path but does not have an attached editor."
                )
                editor = self._create_editor(user, identity)
                created = True
            except:
                raise PermissionDenied
        return user, created

    def authenticate(self, request=None, access_token=None, handshaker=None):
        logger.info("Authenticating user...")
        if not request or not access_token or not handshaker:
            logger.info(
                "Missing OAuth authentication elements; falling back"
                "to another authentication method."
            )
            # You must have meant to use a different authentication backend.
            # Returning None will make Django keep going down its list of
            # options.
            return None

        try:
            assert isinstance(access_token, AccessToken)
        except AssertionError as e:
            logger.exception(e)
            return None

        # Get identifying information about the user. This doubles as a way
        # to authenticate the access token, which only Wikimedia can do,
        # and thereby to authenticate the user (which is hard for us to do as
        # we have no password.)
        logger.info("Identifying user...")
        try:
            identity = handshaker.identify(access_token, 15)
        except OAuthException as e:
            contact_url = reverse("contact")
            logger.warning(e)
            # Translators: The message shown for the contact link
            # to the Wikipedia Library team upon errors when logging in.
            contact_message = _("contact The Wikipedia Library team")
            messages.warning(
                request,
                # Translators: This error message is shown when there's a problem with the authenticated login process.
                mark_safe(
                    # fmt: off
                    _("There was a problem with the access token. Please try again later or {contact_link} if the problem persists.")
                    # fmt: on
                    .format(
                        contact_link="<a href='"
                        + contact_url
                        + "' class='twl-links' target='_blank' rel='noopener noreferrer'>"
                        + contact_message
                        + "</a>"
                    )
                ),
            )
            raise PermissionDenied

        # Get or create the user.
        logger.info("User has been identified; getting or creating user.")
        user, created = self._get_and_update_user_from_identity(identity)

        if created:
            try:
                user.editor.save()
            except AssertionError:
                # This was used to handle users not setting a home wiki
                # but that information is no longer collected
                pass
        else:
            logger.info("User has been updated.")

        request.session["user_created"] = created

        # Checking if more than one session exists
        sessions = Session.objects.filter(account_id=user.pk)
        if sessions.exists():
            logger.info("Deleting all previous sessions.")
            sessions.delete()

        # The authenticate() function of a Django auth backend must return
        # the user.
        return user

    # Implementation for
    # https://docs.djangoproject.com/en/4.2/ref/contrib/auth/#django.contrib.auth.get_user
    def get_user(self, user_id):
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            logger.warning("OAuthBackend.get_user: User does not exist")
        return user


class OAuthInitializeView(View):
    """
    Ask Wikipedia for a temporary key/secret for the user, and redirect
    them to their home Wikipedia to confirm authorization.
    """

    def get(self, request, *args, **kwargs):
        # The site might be running under multiple URLs, so find out the current
        # one (and make sure it's legit).
        # The Sites framework was designed for different URLs that correspond to
        # different databases or functionality - it's not a good fit here.
        domain = self.request.get_host()
        user = self.request.user
        user_preferred_lang_set = False

        try:
            assert domain in settings.ALLOWED_HOSTS  # safety first!
        except (AssertionError, DisallowedHost) as e:
            logger.exception(e)
            messages.warning(
                request,
                # Translators: This message is shown when the OAuth login process fails because the request came from the wrong website. Don't translate {domain}.
                _("{domain} is not an allowed host.").format(domain=domain),
            )
            raise PermissionDenied

        # Try to capture the relevant page state, including desired destination
        try:
            request.session["get"] = request.GET
            logger.info("Found get parameters for post-login redirection.")
        except Exception as e:
            logger.warning(e)
            pass

        # If the user has already logged in, let's not spam the OAuth provider.
        if user.is_authenticated:
            # We're using this twice. Not very DRY.
            # Send user either to the destination specified in the 'next'
            # parameter or to their own editor detail page.
            try:
                # Create a QueryDict from the 'get' session dict.
                query_dict = QueryDict(urlencode(request.session["get"]), mutable=True)
                # Pop the 'next' parameter out of the QueryDict.
                next = query_dict.pop("next")
                return_url = _sanitize_next_url(next=next)
                if return_url is not None:
                    # Pop the 'from_homepage' parameter out of the QueryDict.
                    # We don't need it here.
                    query_dict.pop("from_homepage", None)
                    # If there is anything left in the QueryDict after popping
                    # 'next', append it to the return url. This preserves state
                    # for filtered lists and redirected form submissions like
                    # the partner suggestion form.
                    if query_dict:
                        return_url += "&" + urlencode(query_dict)
                else:
                    return_url = reverse_lazy("homepage")
                logger.info(
                    "User is already authenticated. Sending them on "
                    'for post-login redirection per "next" parameter.'
                )
            except KeyError as e:
                return_url = reverse_lazy("homepage")
                logger.warning(e)

            response = HttpResponseRedirect(return_url)
            user_preferred_lang_set = _check_user_preferred_language(user)
            if user_preferred_lang_set:
                logger.info(
                    "User has preferred language different from browser language; setting language to preferred one..."
                )
                translation_activate(user.userprofile.lang)
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME, user.userprofile.lang
                )

            return response
        # If the user isn't logged in
        else:
            # Get handshaker for the configured wiki oauth URL.
            handshaker = _get_handshaker()
            logger.info("Handshaker obtained from OAuthInitialize.")

            try:
                redirect, request_token = handshaker.initiate()
            except OAuthException as e:
                logger.warning(e)
                messages.warning(
                    request,
                    # Translators: This warning message is shown to users when OAuth handshaker can't be initiated.
                    _("Handshaker not initiated, please try logging in again."),
                )
                raise PermissionDenied

            # Create a QueryDict from the 'get' session dict.
            query_dict = QueryDict(urlencode(request.session["get"]), mutable=True)
            # Pop the 'next' parameter out of the QueryDict.
            next = query_dict.pop("next")
            # Set the return url to the value of 'next'. Basic.
            return_url = next[0]
            # Pop the 'from_homepage' parameter out of the QueryDict.
            from_homepage = query_dict.pop("from_homepage", None)

            if from_homepage:
                logger.info("Logging in from homepage, redirecting to Meta login")
                local_redirect = _localize_oauth_redirect(redirect)
            else:
                logger.info(
                    "Trying to access a link while not logged in, redirecting to homepage"
                )
                messages.info(
                    request,
                    # fmt: off
                    # Translators: this message is displayed to users that don't have accounts and clicked on a proxied link.
                    _("To view this link you need to be an eligible library user. Please login to continue."),
                    # fmt: on
                )
                if return_url:
                    homepage = reverse_lazy("homepage")
                    local_redirect = "{homepage}?next_url={return_url}".format(
                        homepage=homepage, return_url=return_url
                    )
                else:
                    local_redirect = reverse_lazy("homepage")

            logger.info("Handshaker initiated in OAuthInitialize.")
            self.request.session["request_token"] = _dehydrate_token(request_token)

            return HttpResponseRedirect(local_redirect)


class OAuthCallbackView(View):
    """
    Receive the redirect from Wikipedia and parse the response token.
    """

    def get(self, request, *args, **kwargs):
        request_meta_qs = request.META["QUERY_STRING"]
        request_get = request.GET
        response_qs = None
        user_preferred_lang_set = False

        if request_meta_qs:
            response_qs = request_meta_qs
        elif "oauth_token" in request_get and "oauth_verifier" in request_get:
            response_qs = request_get.urlencode()

        try:
            response_qs_parsed = urllib.parse.parse_qs(response_qs)
            assert "oauth_token" in response_qs_parsed
            assert "oauth_verifier" in response_qs_parsed
        except (AssertionError, TypeError) as e:
            logger.warning(e)
            messages.warning(
                request,
                # Translators: This warning message is shown to users when the response received from Wikimedia OAuth servers is not a valid one.
                _("Did not receive a valid oauth response."),
            )
            raise PermissionDenied

        # Get the handshaker. It should have already been constructed by
        # OAuthInitializeView.
        domain = self.request.get_host()
        try:
            assert domain in settings.ALLOWED_HOSTS
        except (AssertionError, DisallowedHost) as e:
            logger.warning(e)
            messages.warning(
                request,
                # Translators: This message is shown when the OAuth login process fails because the request came from the wrong website. Don't translate {domain}.
                _("{domain} is not an allowed host.").format(domain=domain),
            )
            raise PermissionDenied

        try:
            handshaker = _get_handshaker()
            logger.info("Hanshaker obtained for OAuthCallback")
        except AssertionError as e:
            # get_handshaker will throw AssertionErrors for invalid data.
            logger.warning(e)
            messages.warning(
                request,
                # Translators: This message is shown when the OAuth login process fails.
                _("Could not find handshaker."),
            )
            raise PermissionDenied

        # Get the session token placed by OAuthInitializeView.
        session_token = request.session.pop("request_token", None)

        if not session_token:
            logger.info("No session token.")
            messages.warning(
                request,
                # Translators: This message is shown when the OAuth login process fails.
                _("No session token."),
            )
            raise PermissionDenied

        # Rehydrate it into a request token.
        request_token = _rehydrate_token(session_token)

        if not request_token:
            logger.warning("No request token.")
            messages.warning(
                request,
                # Translators: This message is shown when the OAuth login process fails.
                _("No request token."),
            )
            raise PermissionDenied

        # See if we can complete the OAuth process.
        access_token = None
        try:
            access_token = handshaker.complete(request_token, response_qs)
        # Send exceptions to glitchtip
        except OAuthException as e:
            logger.warning(e)
            capture_exception(e)
        # raise an error if we don't have an access token
        if not access_token:
            messages.warning(
                request,
                # Translators: This message is shown when the OAuth login process fails.
                _("Access token generation failed, please try logging in again."),
            )
            # @TODO: revert the following after T332650 is resolved
            # raise PermissionDenied
            messages.warning(
                request,
                mark_safe(
                    # fmt: off
                    # Translators: This message is shown when more information is available on another page. Do not translate {issue}
                    _("See {issue} for more information").format(
                        issue="<a href='https://phabricator.wikimedia.org/T332650' target='_blank' rel='noopener noreferrer'>T332650</a>"
                    )
                    # fmt: on
                ),
            )

        user = authenticate(
            request=request, access_token=access_token, handshaker=handshaker
        )
        created = request.session.pop("user_created", False)

        if user and not user.is_active:
            # Do NOT log in the user.

            if created:
                messages.warning(
                    request,
                    # fmt: off
                    # Translators: If the user tries to log in, but their account does not meet certain requirements, they cannot login.
                    _("Your Wikipedia account does not meet the eligibility criteria in the terms of use, so your Wikipedia Library Card Platform account cannot be activated."),
                    # fmt: on
                )
            else:
                messages.warning(
                    request,
                    # fmt: off
                    # Translators: If the user tries to log in, but their account does not meet certain requirements, they cannot login.
                    _("Your Wikipedia account no longer meets the eligibility criteria in the terms of use, so you cannot be logged in. If you think you should be able to log in, please email wikipedialibrary@wikimedia.org."),
                    # fmt: on
                )

            return_url = reverse_lazy("terms")
        elif user:
            login(request, user)

            if created:
                messages.info(
                    request,
                    # Translators: this message is displayed to users with brand new accounts.
                    _("Welcome! Please agree to the terms of use."),
                )
                return_url = reverse_lazy("terms")
            else:
                # We're using this twice. Not very DRY.
                # Send user either to the destination specified in the 'next'
                # parameter or to their own editor detail page.
                if user.userprofile.terms_of_use:
                    try:
                        # Create a QueryDict from the 'get' session dict.
                        query_dict = QueryDict(
                            urlencode(request.session["get"]), mutable=True
                        )
                        # Pop the 'next' parameter out of the QueryDict.
                        next = query_dict.pop("next")
                        return_url = _sanitize_next_url(next=next)
                        if return_url is not None:
                            # Pop the 'from_homepage' parameter out of the QueryDict.
                            # We don't need it here.
                            query_dict.pop("from_homepage", None)
                            # If there is anything left in the QueryDict after popping
                            # 'next', append it to the return url. This preserves state
                            # for filtered lists and redirected form submissions like
                            # the partner suggestion form.
                            if query_dict:
                                return_url += "&" + urlencode(query_dict)
                            logger.info(
                                "User authenticated. Sending them on for "
                                'post-login redirection per "next" parameter.'
                            )
                        else:
                            return_url = reverse_lazy("homepage")
                    except KeyError as e:
                        return_url = reverse_lazy("homepage")
                        logger.warning(e)
                else:
                    return_url = reverse_lazy("terms")

            user_preferred_lang_set = _check_user_preferred_language(user)
        else:
            return_url = reverse_lazy("homepage")

        response = HttpResponseRedirect(return_url)
        if user_preferred_lang_set:
            logger.info(
                "User has preferred language different from browser language; setting language to preferred one...."
            )
            translation_activate(user.userprofile.lang)
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user.userprofile.lang)

        return response
