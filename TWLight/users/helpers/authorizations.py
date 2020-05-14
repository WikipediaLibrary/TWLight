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


def get_valid_partner_authorizations(partner_pk, stream_pk=None):
    """
    Retrieves the valid authorizations available for a particular
    partner (or collections if stream_pk is not None). Valid authorizations are
    authorizations with which we can operate, and is decided by certain conditions as
    spelled out in the is_valid property of the Authorization model object (users/models.py).
    """
    today = datetime.date.today()
    try:
        # The filter below is equivalent to retrieving all authorizations for a partner
        # and (or) stream and checking every authorization against the is_valid property
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
        if stream_pk:
            valid_authorizations = valid_authorizations.filter(stream=stream_pk)

        return valid_authorizations
    except Authorization.DoesNotExist:
        return Authorization.objects.none()


def sort_authorizations_into_my_library_list(authorizations):
    """
    Given a queryset of Authorization objects, return a
    list of dictionaries, sorted alphabetically by partner
    or stream name, with additional data computed for ease
    of display in the my_library template.
    """
    authorization_list = []
    if authorizations:
        for authorization in authorizations:
            for partner in authorization.partners.all():
                # Name this item according to whether this authorization is
                # to a stream
                stream = authorization.stream
                if stream:
                    name_string = stream.name
                else:
                    name_string = partner.company_name
                authorization_list.append({"name": name_string})
                this_item = authorization_list[-1]

                this_item["partner"] = partner
                this_item["authorization"] = authorization
                this_item["stream"] = stream
                if stream:
                    access_url = stream.get_access_url
                else:
                    access_url = partner.get_access_url
                this_item["access_url"] = access_url

                valid_authorization = authorization.is_valid
                this_item['valid_proxy_authorization'] = partner.authorization_method == partner.PROXY and valid_authorization
                this_item['valid_authorization_with_access_url'] = access_url and valid_authorization and authorization.user.userprofile.terms_of_use

        # Alphabetise by name
        authorization_list = sorted(authorization_list, key=lambda i: i["name"])

        return authorization_list
    else:
        return None
