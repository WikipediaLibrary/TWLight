import datetime

from django.db.models import Q

from TWLight.resources.models import Partner
from TWLight.users.models import Authorization


def get_all_bundle_authorizations():
    """
    Returns all Bundle authorizations, both active
    and not.
    """

    return Authorization.objects.filter(
        partners__authorization_method=Partner.BUNDLE
    ).distinct()  # distinct() required because partners__authorization_method is ManyToMany


def get_valid_partner_authorizations(partner_pk):
    """
    Retrieves the valid authorizations available for a particular
    partner. Valid authorizations are authorizations with which we can operate,
    and is decided by certain conditions as spelled out in the is_valid property
    of the Authorization model object (users/models.py).
    """
    today = datetime.date.today()
    try:
        # The filter below is equivalent to retrieving all authorizations for a partner
        # and checking every authorization against the is_valid property
        # of the authorization model, and hence *must* be kept in sync with the logic in
        # TWLight.users.model.Authorization.is_valid property. We don't need to check for
        # partner_id__isnull since it is functionally covered by partners=partner_pk.
        valid_authorizations = Authorization.objects.filter(
            Q(date_expires__isnull=False, date_expires__gte=today)
            | Q(date_expires__isnull=True),
            authorizer__isnull=False,
            user__isnull=False,
            date_authorized__isnull=False,
            date_authorized__lte=today,
            partners=partner_pk,
        )

        return valid_authorizations
    except Authorization.DoesNotExist:
        return Authorization.objects.none()


def create_resource_dict(authorization, partner):
    resource_item = {
        "partner": partner,
        "authorization": authorization,
    }

    access_url = partner.get_access_url
    resource_item["access_url"] = access_url

    valid_authorization = authorization.is_valid
    resource_item["valid_proxy_authorization"] = (
        partner.authorization_method == partner.PROXY and valid_authorization
    )
    resource_item["valid_authorization_with_access_url"] = (
        access_url
        and valid_authorization
        and authorization.user.userprofile.terms_of_use
    )

    return resource_item


def delete_duplicate_bundle_authorizations(authorizations):
    """
    Given a queryset of Authorization objects,
    delete duplicate Bundle authorizations.
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


def sort_authorizations_into_resource_list(authorizations):
    """
    Given a queryset of Authorization objects, return a
    list of dictionaries, sorted alphabetically by partner
    name, with additional data computed for ease of display
    in the my_library template.
    """
    resource_list = []
    if authorizations:
        for authorization in authorizations:
            for partner in authorization.partners.all():
                resource_list.append(create_resource_dict(authorization, partner))

        # Alphabetise by name
        resource_list = sorted(
            resource_list, key=lambda i: i["partner"].company_name.lower()
        )

        return resource_list
    else:
        return None
