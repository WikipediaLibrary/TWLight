from django.core.cache import cache
from django.dispatch import receiver
from django.db.models.signals import post_save
from TWLight.resources.models import Partner, PhabricatorTask


@receiver(post_save, sender=Partner)
@receiver(post_save, sender=PhabricatorTask)
def delete_all_cache(sender, instance, **kwargs):
    """Clear all cache after saving objects that impaced cached pages across the site."""
    cache.clear()
