from datetime import timedelta
from django.contrib.auth.models import User
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from TWLight.users.models import Authorization
from TWLight.resources.models import Partner, Stream


class Notice(object):
    user_renewal_notice = Signal(
        providing_args=[
            "user_wp_username",
            "user_email",
            "user_lang",
            "partner_name",
            "partner_link",
        ]
    )


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

    if partner.account_length or partner.authorization_method == Partner.PROXY:
        authorizations = Authorization.objects.filter(
            partner=partner, date_expires=None
        )
        for authorization in authorizations:
            if authorization.is_valid:
                if (
                    partner.authorization_method == Partner.PROXY
                    and partner.requested_access_duration is True
                ):
                    one_year_from_auth = authorization.date_authorized + timedelta(
                        days=365
                    )
                    authorization.date_expires = one_year_from_auth
                    authorization.save()
                elif partner.account_length:
                    authorization.date_expires = (
                        authorization.date_authorized + partner.account_length
                    )
                    authorization.save()


@receiver(post_delete, sender=Stream)
def delete_all_but_latest_partner_authorizations(sender, instance, **kwargs):
    """
    Deletes any duplicate partner auths left after a stream is deleted.
    """

    partner = instance.partner
    authorizations = Authorization.objects.filter(partner=partner)
    users = User.objects.filter(authorization__in=authorizations)
    for user in users:
        partner_authorizations = Authorization.objects.filter(
            user=user, partner=partner, stream__isnull=True
        )
        if partner_authorizations.count() > 1:
            latest_partner_authorization = partner_authorizations.latest(
                "date_authorized"
            )
            partner_authorizations.exclude(pk=latest_partner_authorization.pk).delete()
