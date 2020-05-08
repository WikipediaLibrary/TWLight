from TWLight.resources.models import Partner
from TWLight.users.models import Authorization


# We have to put this in a new bundle_authorizations.py helper
# rather than authorizations.py to avoid circular imports
def get_all_bundle_authorizations():
    """
    Returns all Bundle authorizations, both active
    and not.
    If no authorizations are found, returns None.
    """

    auths = Authorization.objects.filter(
        partners__authorization_method=Partner.BUNDLE
    ).distinct()

    if auths.exists():
        return auths
    else:
        return None
