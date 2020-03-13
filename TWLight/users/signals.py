from datetime import timedelta
from django.conf import settings
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, post_delete
from TWLight.users.models import Authorization, UserProfile
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


class ProxyBundleLaunch(object):
    launch_notice = Signal(
        providing_args=[
            "user_wp_username",
            "user_email",
        ]
    )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profiles automatically when users are created."""
    if created:
        UserProfile.objects.create(user=instance)


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
    authorizations = Authorization.objects.filter(partner=partner, stream__isnull=True)
    # TODO: Figure out why we were getting bizarre results when this was a queryset.
    users = authorizations.values_list("user", flat=True)
    for user in users:
        user_authorizations = authorizations.filter(user=user)
        if user_authorizations.count() > 1:
            latest_authorization = user_authorizations.latest("date_authorized")
            user_authorizations.exclude(pk=latest_authorization.pk).delete()
