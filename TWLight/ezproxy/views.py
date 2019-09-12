# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import urllib
from time import gmtime
from calendar import timegm
from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    SuspiciousOperation,
    ValidationError,
)
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect
from django.views import View
from TWLight.resources.models import Partner, Stream
from TWLight.users.models import Authorization


class EZProxyAuth(View):
    @staticmethod
    def get(request, url=None, token=None):
        username = request.user.editor.wp_username
        groups = ["Default"]

        if not username:
            raise SuspiciousOperation("Missing Editor username.")

        try:
            authorizations = Authorization.objects.filter(authorized_user=request.user, is_valid=True)
            for authorization in authorizations:
                partner = Partner.objects.get(authorization_method=Partner.PROXY, pk=authorization.partner_id)
                group = ""
                if partner and partner.proxy_enabled:
                    group = "P" + repr(partner.pk)
                    stream = Stream.objects.get(authorization_method=Partner.PROXY, pk=authorization.stream_id)
                    if stream and stream.proxy_enabled:
                        group += "S" + repr(stream.pk)
                if group:
                    groups.append(group)
        except ObjectDoesNotExist:
            pass

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

        if not secret:
            raise SuspiciousOperation(
                "EZProxy Configuration Error: shared secret cannot be empty."
            )

        packet = "$u" + repr(timegm(gmtime()))
        if groups:
            packet += "$g" + "+".join(groups)

        packet += "$e"
        ticket = urllib.quote(
            hashlib.sha512(secret + user + packet).hexdigest() + packet
        )
        self.starting_point_url = (
                ezproxy_url + "/login?user=" + user + "&ticket=" + ticket
        )

    def url(self, url):
        return self.starting_point_url + "&url=" + url
