from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key


def invalidate_cache(user_language, partner_pk):
    short_description_cache_key = make_template_fragment_key(
        'partner_short_description', [user_language, partner_pk]
    )
    cache.delete(short_description_cache_key)