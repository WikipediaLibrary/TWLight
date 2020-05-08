from TWLight.resources.models import Partner
from TWLight.users.models import Authorization


# We have to put this in a new bundle_authorizations.py helper
# rather than authorizations.py to avoid circular imports
def get_all_bundle_authorizations():
    """
    Returns all Bundle authorizations, both active
    and not.
    """

    return Authorization.objects.filter(
        partners__authorization_method=Partner.BUNDLE
    ).distinct()  # distinct() required because partners__authorization_method is ManyToMany
