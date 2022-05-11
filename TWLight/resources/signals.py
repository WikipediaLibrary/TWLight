from django.core.cache import cache
from django.dispatch import receiver, Signal
from django.db.models.signals import pre_save, post_save, post_delete
from TWLight.resources.models import Partner


@receiver(post_save, sender=Partner)
def delete_all_cache(sender, instance, **kwargs):
    """Partner updates impact cached pages across the site, so clear all cache after saving."""
    if sender == Partner:
        cache.clear()
