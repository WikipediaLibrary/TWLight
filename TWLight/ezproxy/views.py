# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
from time import gmtime
from calendar import timegm
from django.conf import settings
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect
from django.views import View



class EZProxyAuth(View):

  def get(self, request, url):
      username = request.user.editor.wp_username

      if not url:
        raise SuspiciousOperation('Missing EZProxy target URL.')

      if not username:
          raise SuspiciousOperation('Missing Editor username.')

      try:
          validate = URLValidator(schemes=('http', 'https'))
          validate(url)
      except ValidationError:
          raise SuspiciousOperation('Invalid EZProxy target URL.')

      return HttpResponseRedirect(EZProxyTicket(username).url(url))


class EZProxyTicket(object):

  starting_point_url = None

  def __init__(self, user, groups=''):

    ezproxy_url = settings.TWLIGHT_EZPROXY_URL
    secret = settings.TWLIGHT_EZPROXY_SECRET

    if not secret:
      raise SuspiciousOperation('EZProxy Configuration Error: shared secret cannot be empty.')

    packet = '$u' + repr(timegm(gmtime()))
    if groups:
      packet +=  '$g' + groups

    packet += '$e'
    ticket = hashlib.sha512(secret + user + packet).hexdigest() + packet
    self.starting_point_url = ezproxy_url + "/login?user=" +  user + "&ticket=" + ticket

  def url(self, url):
    return self.starting_point_url + "&url=" + url
