from datetime import timedelta
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from TWLight.users.models import Authorization
from .models import Partner, Stream


class Notice(object):
    user_renewal_notice = Signal(providing_args=['user_wp_username', 'user_email', 'user_lang', 'partner_name', 'partner_link'])



@receiver(post_save, sender=Partner)
@receiver(post_save, sender=Stream)
def update_partner_authorization_expiry(sender, instance, **kwargs):
    """
    Updates missing expiration dates upon resource updates.
    Mostly cribbed from
    TWLight.applications.models.post_receive_commit
    and
    TWLight.users.management.commands.authorization_backfill
    Could factor out the common code.
    """

    if sender == Partner:
        partner = instance
    elif sender == Stream:
        partner = instance.partner

    if partner.account_length or partner.requested_access_duration:
        authorizations = Authorization.objects.filter(partner=partner)
        for authorization in authorizations:
            if authorization.is_valid and not authorization.date_expires:
                if partner.authorization_method == Partner.PROXY and partner.requested_access_duration is True:
                    one_year_from_auth = authorization.date_authorized + timedelta(days=365)
                    authorization.date_expires = one_year_from_auth
                    authorization.save()
                elif partner.account_length:
                    authorization.date_expires = authorization.date_authorized + partner.account_length
                    authorization.save()
