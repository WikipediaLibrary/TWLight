# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import logging
import urllib
from time import gmtime
from calendar import timegm
from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation, ValidationError
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect
from django.views import View
from TWLight.resources.models import Partner, Stream
from TWLight.users.models import Authorization

logger = logging.getLogger(__name__)


class EZProxyAuth(View):
    @staticmethod
    def get(request, url=None, token=None):
        username = request.user.editor.wp_username
        groups = []

        if not username:
            raise SuspiciousOperation("Missing Editor username.")

        try:
            authorizations = Authorization.objects.filter(authorized_user=request.user)
            logger.info(
                "Editor {username} has the following authorizations: {authorizations}.".format(
                    username=username, authorizations=authorizations
                )
            )
        except Authorization.DoesNotExist:
            authorizations = None

        for authorization in authorizations:
            if authorization.is_valid:
                group = ""
                try:
                    partner = Partner.objects.get(
                        authorization_method=Partner.PROXY, pk=authorization.partner_id
                    )
                    group += "P" + repr(partner.pk)
                    try:
                        stream = Stream.objects.get(
                            authorization_method=Partner.PROXY,
                            pk=authorization.stream_id,
                        )
                        group += "S" + repr(stream.pk)
                    except Stream.DoesNotExist:
                        pass
                except Partner.DoesNotExist:
                    pass

                groups.append(group)
                logger.info("{group}.".format(group=group))

        if url:
            try:
                validate = URLValidator(schemes=("http", "https"))
                validate(url)
            except ValidationError:
                raise SuspiciousOperation("Invalid EZProxy target URL.")
        elif token:
            url = token
        else:
            raise SuspiciousOperation("Missing EZProxy target URL.")

        return HttpResponseRedirect(EZProxyTicket(username, groups).url(url))


class EZProxyTicket(object):
    starting_point_url = None

    def __init__(self, user, groups=None):

        ezproxy_url = settings.TWLIGHT_EZPROXY_URL
        secret = settings.TWLIGHT_EZPROXY_SECRET

        # Clearly not allowed if the user isn't in any proxy groups.
        if not groups:
            raise PermissionDenied(
                "You are not authorized to access this resource."
            )

        if not secret:
            raise SuspiciousOperation(
                "EZProxy Configuration Error: shared secret cannot be empty."
            )

        packet = "$u" + repr(timegm(gmtime()))
        packet += "$g" + "+".join(groups)
        packet += "$e"

        logger.info(
            "Editor {username} has the following EZProxy group packet: {packet}.".format(
                username=user, packet=packet
            )
        )
        ticket = urllib.quote(
            hashlib.sha512(secret + user + packet).hexdigest() + packet
        )
        self.starting_point_url = (
            ezproxy_url + "/login?user=" + user + "&ticket=" + ticket
        )

    def url(self, url):
        return self.starting_point_url + "&url=" + url
