import warnings

from django.conf import settings
from django.conf.urls import url
from django.core.urlresolvers import LocaleRegexURLResolver
from django.utils import six
from TWLight.i18n.views import set_language

# Direct rip from django.conf.urls.i18n, but imports our local set_language
# https://docs.djangoproject.com/en/1.8/_modules/django/conf/urls/i18n/

def i18n_patterns(prefix, *args):
    """
    Adds the language code prefix to every URL pattern within this
    function. This may only be used in the root URLconf, not in an included
    URLconf.
    """
    if isinstance(prefix, six.string_types):
        pattern_list = patterns(prefix, *args)
    else:
        pattern_list = [prefix] + list(args)
    if not settings.USE_I18N:
        return pattern_list
    return [LocaleRegexURLResolver(pattern_list)]



urlpatterns = [
    url(r'^setlang/$', set_language, name='set_language'),
]
