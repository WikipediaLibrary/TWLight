from django import template
import urllib.request, urllib.error, urllib.parse

register = template.Library()

# Cribbed from coderwall
# https://coderwall.com/p/4zcoxa/urlencode-filter-in-jinja2


@register.filter
def urlencode(value):
    """Passes string through urlencode"""
    output = urllib.parse.quote(value)
    return output
