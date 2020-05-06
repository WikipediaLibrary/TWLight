from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.dispatch import receiver, Signal
from django.db.models.signals import pre_save, post_save, post_delete
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
    launch_notice = Signal(providing_args=["user_wp_username", "user_email"])


@receiver(pre_save, sender=Authorization)
def validate_authorization(sender, instance, **kwargs):
    """Authorizations are generated by app code instead of ModelForm, so full_clean() before saving."""
    instance.full_clean()


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
            partners=partner, date_expires=None
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
    authorizations = Authorization.objects.filter(partners=partner, stream__isnull=True)
    # TODO: Figure out why we were getting bizarre results when this was a queryset.
    users = authorizations.values_list("user", flat=True)
    for user in users:
        user_authorizations = authorizations.filter(user=user)
        if user_authorizations.count() > 1:
            latest_authorization = user_authorizations.latest("date_authorized")
            user_authorizations.exclude(pk=latest_authorization.pk).delete()


@receiver(pre_save, sender=Partner)
def update_existing_bundle_authorizations(sender, instance, **kwargs):
    """
    If this partner was just switched to Bundle from a non-Bundle
    authorization method, update any existing Bundle authorizations
    to include it, and vice-versa, including if it was marked not-available.
    """
    add_to_auths = False
    remove_from_auths = False

    try:
        previous_data = Partner.even_not_available.get(
            pk=instance.pk
        )
    # We must be creating this partner, we'll handle this case in a
    # post-save signal
    except Partner.DoesNotExist:
        return

    # New data for this partner for readability
    now_bundle = instance.authorization_method == Partner.BUNDLE
    now_available = instance.status == Partner.AVAILABLE
    now_not_available = instance.status == Partner.NOT_AVAILABLE

    # Previous data for this partner for readability
    previously_available = previous_data.status == Partner.AVAILABLE
    previously_not_available = previous_data.status == Partner.NOT_AVAILABLE
    previously_bundle = previous_data.authorization_method == Partner.BUNDLE

    if now_available:
        if now_bundle:
            if previously_not_available or not previously_bundle:
                add_to_auths = True
        else:
            if previously_bundle:
                remove_from_auths = True

    elif now_not_available:
        if previously_available and previously_bundle:
            remove_from_auths = True

    # Let's avoid db queries if we don't need them
    if add_to_auths or remove_from_auths:
        authorizations_to_update = Authorization.objects.filter(
            partners__authorization_method=Partner.BUNDLE,
        ).distinct()

        if add_to_auths:
            for authorization in authorizations_to_update:
                authorization.partners.add(instance)
        elif remove_from_auths:
            for authorization in authorizations_to_update:
                authorization.partners.remove(instance)


@receiver(post_save, sender=Partner)
def update_bundle_authorizations_on_bundle_partner_creation(sender, instance, created, **kwargs):
    """
    This does the same thing that the pre-save signal update_existing_bundle_authorizations()
    does, except it handles new Bundle-partner creations. We can't do this in
    pre-save because the partner object doesn't exist yet.
    """
    if created and instance.status == Partner.AVAILABLE and instance.authorization_method == Partner.BUNDLE:
        authorizations_to_update = Authorization.objects.filter(
            partners__authorization_method=Partner.BUNDLE,
        ).distinct()

        for authorization in authorizations_to_update:
            authorization.partners.add(instance)
