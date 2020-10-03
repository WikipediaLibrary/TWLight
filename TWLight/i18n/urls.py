from django.conf import settings
from django.conf.urls import url
from django.urls import LocalePrefixPattern, URLResolver, get_resolver, path
from TWLight.i18n.views import set_language

# Direct rip from django.conf.urls.i18n, but imports our local set_language
# from GitHub


def i18n_patterns(*urls, prefix_default_language=True):
    """
    Add the language code prefix to every URL pattern within this function.
    This may only be used in the root URLconf, not in an included URLconf.
    """
    if not settings.USE_I18N:
        return list(urls)
    return [
        URLResolver(
            LocalePrefixPattern(prefix_default_language=prefix_default_language),
            list(urls),
        )
    ]


urlpatterns = [path("setlang/", set_language, name="set_language")]
