import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand, CommandError
from TWLight.users.models import Authorization, Partner
from TWLight.applications.models import Application

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Creates missing authorizations based on existing setnt applications
    Mostly cribbed from TWLight.applications.models.post_receive_commit. Could factor out the common code.
    """

    def handle(self, **options):
        # Get sent applications with an available partner and editor. We're sorting by ascending date to back-fill
        # authorizations from oldest to newest.
        sent_applications = Application.objects.filter(
            status=Application.SENT,
            editor__isnull=False,
            partner__isnull=False,
            partner__status=0,
        ).order_by("date_created", "editor", "partner")
        for application in sent_applications:
            existing_authorization = Authorization.objects.filter(
                user=application.user, partners=application.partner
            )
            # In the case that there is no existing authorization, create a new one
            if existing_authorization.count() == 0:
                authorization = Authorization()
                authorization.user = application.user
                authorization.authorizer = application.sent_by
                # You can't set the date_authorized on creation, but you can modify it afterwards. So save immediately.
                authorization.save()
                # We set the authorization date to the date the application was closed.
                authorization.date_authorized = application.date_closed
                authorization.partners.add(application.partner)
                # If this is a proxy partner, and the requested_access_duration
                # field is set to false, set (or reset) the expiry date
                # to one year from authorization.
                if (
                    application.partner.authorization_method == Partner.PROXY
                    and application.requested_access_duration is None
                ):
                    one_year_from_auth = authorization.date_authorized + timedelta(
                        days=365
                    )
                    authorization.date_expires = one_year_from_auth
                # If this is a proxy partner, and the requested_access_duration
                # field is set to true, set (or reset) the expiry date
                # to 1, 3, 6 or 12 months from authorization based on user input
                elif (
                    application.partner.authorization_method == Partner.PROXY
                    and application.partner.requested_access_duration is True
                ):
                    custom_expiry_date = authorization.date_authorized + relativedelta(
                        months=+application.requested_access_duration
                    )
                    authorization.date_expires = custom_expiry_date
                # Alternatively, if this partner has a specified account_length,
                # we'll use that to set the expiry.
                elif application.partner.account_length:
                    # account_length should be a timedelta
                    authorization.date_expires = (
                        authorization.date_authorized
                        + application.partner.account_length
                    )

                authorization.save()
                logger.info(
                    "authorization created: {authorization}".format(
                        authorization=authorization
                    )
                )
