from django.dispatch import receiver
from django.db.models.signals import post_delete
from TWLight.resources.models import Stream


@receiver(post_delete, sender=Stream)
def set_partner_specific_stream_false_if_no_streams(sender, instance, **kwargs):
    """
    Set parent partner's specific_stream to False when the last stream is deleted.
    """

    partner = instance.partner
    if partner.specific_stream and Stream.objects.filter(partner=partner).count() == 0:
        partner.specific_stream = False
        partner.save()
