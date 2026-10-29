from django.db.models import QuerySet

from TWLight.resources.models import Partner
from TWLight.users.models import Authorization


def get_all_bundle_authorizations():
    """
    Returns all Bundle authorizations, both active
    and not.

    Returns
    -------
    QuerySet
    """

    # distinct() required because partners__authorization_method is ManyToMany
    return (
        Authorization.objects.select_for_update()
        .filter(partners__authorization_method=Partner.BUNDLE)
        .distinct()
    )


def delete_duplicate_bundle_authorizations(authorizations: QuerySet):
    """
    Given a queryset of Authorization objects, find the ones which are
    Bundle authorizations, then locate and delete any duplicates for
    each user.

    Parameters
    ----------
    authorizations: QuerySet
        Queryset of Authorization objects to check for duplicates.
    """
    bundle_authorizations = authorizations.filter(
        partners__authorization_method=Partner.BUNDLE
    )
    # Get a list of users with bundle auths
    for user_id in bundle_authorizations.values_list("user_id"):
        # get the distinct set of authorizations for the user
        user_authorizations = bundle_authorizations.filter(user_id=user_id).distinct()
        # There should be no more than one bundle auth per user, so slice the queryest to get any auths beyond that
        for duplicate_authorization in user_authorizations[1:].iterator():
            # Delete it
            duplicate_authorization.delete()
