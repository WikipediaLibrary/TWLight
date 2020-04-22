from typing import Union
from django.db.models import QuerySet
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from modeltranslation.manager import MultilingualQuerySet
from TWLight.resources.models import Partner


def validate_partners(partners: Union[QuerySet, MultilingualQuerySet]):
    """
    If we have more than one partner, assert that the auth method is the same for all partners and is bundle.
    """
    if partners.count() > 1:
        authorization_methods = (
            partners.all().values_list("authorization_method", flat=True).distinct()
        )

        if authorization_methods.count() > 1:
            raise ValidationError(
                _("All related Partners must share the same Authorization method.")
            )
        if authorization_methods.get() is not Partner.BUNDLE:
            raise ValidationError(
                _("Only Bundle Partners support shared Authorization.")
            )
