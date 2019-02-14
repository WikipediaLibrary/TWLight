from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

"""
Invalidate the different types of descriptions in cache, given the
descriptions are updated on Meta.
"""
def invalidate_short_description_cache(user_language, partner_pk):
    short_description_cache_key = make_template_fragment_key(
        'partner_short_description', [user_language, partner_pk]
    )
    cache.delete(short_description_cache_key)


def invalidate_long_description_cache(user_language, partner_pk):
    long_description_cache_key = make_template_fragment_key(
        'partner_long_description', [user_language, partner_pk]
    )
    cache.delete(long_description_cache_key)


def invalidate_stream_description_cache(user_language, partner_pk):
    stream_description_cache_key = make_template_fragment_key(
        'stream_description', [user_language, partner_pk]
    )
    cache.delete(stream_description_cache_key)