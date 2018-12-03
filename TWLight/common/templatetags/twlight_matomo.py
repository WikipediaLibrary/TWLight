# -*- coding: utf-8 -*-
"""Matomo template tag."""

from django import template
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site


register = template.Library()


@register.inclusion_tag('matomo.html')
def twlight_matomo_tracking():
    try:
        hostname = settings.MATOMO_HOSTNAME
    except AttributeError:
        hostname = None
    try:
        id = settings.MATOMO_SITE_ID
    except AttributeError:
        id = None
    return {'id': id, 'hostname': hostname}
