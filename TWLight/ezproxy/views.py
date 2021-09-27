# -*- coding: utf-8 -*-


import hashlib
import logging
import urllib.request, urllib.parse, urllib.error
from time import gmtime
from calendar import timegm
from django.conf import settings
from django.core.exceptions import (
    PermissionDenied,
    SuspiciousOperation,
    ValidationError,
)
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from django.views import View

from TWLight.resources.models import Partner
from TWLight.users.models import Authorization
from TWLight.view_mixins import ToURequired

logger = logging.getLogger(__name__)


class EZProxyAuth(ToURequired, View):
    @staticmethod
    def get(request, url=None, token=None):
        username = request.user.editor.wp_username
        groups = []

        if not username:
            # Translators: When a user is being authenticated to access proxied resources, and the request's missing the editor's username, this error text is displayed.
            raise SuspiciousOperation(_("Missing Editor username."))

        if request.user.editor.wp_bundle_authorized:
            groups.append("BUNDLE")

        for authorization in Authorization.objects.filter(user=request.user):
            if (
                authorization.is_valid
                and authorization.get_authorization_method() == Partner.PROXY
            ):
                group = "P" + repr(authorization.partners.get().pk)
                groups.append(group)
                logger.info("{group}.".format(group=group))

        if url:
            try:
                validate = URLValidator(schemes=("http", "https"))
                validate(url)
            except ValidationError:
                # Translators: Error text displayed to users when the target URL to access proxied publisher resources is invalid.
                raise SuspiciousOperation(_("Invalid EZProxy target URL."))
        elif token:
            url = token
        else:
            # Translators: Error text displayed to users when the target URL to access proxied publisher resources is missing.
            raise SuspiciousOperation(_("Missing EZProxy target URL."))

        return HttpResponseRedirect(EZProxyTicket(username, groups).url(url))


class EZProxyTicket(object):
    starting_point_url = None

    def __init__(self, user=None, groups=None):

        ezproxy_url = settings.TWLIGHT_EZPROXY_URL
        secret = settings.TWLIGHT_EZPROXY_SECRET

        # Clearly not allowed if there is no user.
        # Clearly not allowed if the user isn't in any proxy groups.
        if not (groups and user):
            # Translators: Error text displayed to users when they are not allowed to access the publisher resource they are trying to access.
            raise PermissionDenied("You are not authorized to access this resource.")

        if not secret:
            raise SuspiciousOperation(
                "EZProxy Configuration Error: shared secret cannot be empty."
            )

        # All allowed editors get the "Default" group.
        groups.append("Default")

        packet = "$u" + repr(timegm(gmtime()))
        packet += "$g" + "+".join(groups)
        packet += "$e"

        logger.info(
            "Editor {username} has the following EZProxy group packet: {packet}.".format(
                username=user, packet=packet
            )
        )
        ticket = urllib.parse.quote(
            hashlib.sha512(str(secret + user + packet).encode("utf-8")).hexdigest()
            + packet
        )
        self.starting_point_url = (
            # The EZproxy server.
            ezproxy_url
            # The TWLight editor.
            + "/login?user="
            + urllib.parse.quote(user)
            # The editor's authorization ticket.
            + "&ticket="
            + ticket
            # An identifier for this CGI endpoint.
            + "&auth="
            + settings.TWLIGHT_ENV
        )

    def url(self, url):
        return self.starting_point_url + "&url=" + url
