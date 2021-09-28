from typing import Union
from django.db.models import QuerySet
from django.core.exceptions import ValidationError

from TWLight.resources.models import Partner
from TWLight.users.groups import get_coordinators


def validate_partners(partners: QuerySet):
    """
    If we have more than one partner, assert that the auth method is the same for all partners and is bundle.
    """
    if partners.count() > 1:
        authorization_methods = (
            partners.all().values_list("authorization_method", flat=True).distinct()
        )

        if authorization_methods.count() > 1:
            raise ValidationError(
                "All related Partners must share the same Authorization method."
            )
        if authorization_methods.get() is not Partner.BUNDLE:
            raise ValidationError("Only Bundle Partners support shared Authorization.")


def validate_authorizer(authorizer):
    coordinators = get_coordinators()
    authorizer_is_coordinator = authorizer in coordinators.user_set.all()
    if not authorizer or not (
        authorizer_is_coordinator
        or authorizer.is_staff
        or authorizer.username == "TWL Team"
    ):
        raise ValidationError(
            "Authorization authorizer must be a coordinator or staff."
        )
