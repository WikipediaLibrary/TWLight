from __future__ import absolute_import, unicode_literals
from celery import shared_task

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key


@shared_task
def invalidate_cache(user_language, partner_pk):
    short_description_cache_key = make_template_fragment_key(
        'partner_short_description', [user_language, partner_pk]
    )
    cache.delete(short_description_cache_key)