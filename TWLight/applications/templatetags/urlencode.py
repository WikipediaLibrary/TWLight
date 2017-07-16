from django import template
import urllib2

register = template.Library()

# Cribbed from coderwall
# https://coderwall.com/p/4zcoxa/urlencode-filter-in-jinja2

@register.filter
def urlencode(value):
    """Passes string through urlencode"""
    output = urllib2.quote(value)
    return output
