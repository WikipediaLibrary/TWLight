from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.applications.helpers import count_valid_authorizations
from TWLight.resources.models import Partner

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Un-waitlists proxy partners having at least one inactive authorization."

    def handle(self, *args, **options):
        all_partners = Partner.objects.filter(
            authorization_method=Partner.PROXY, status=Partner.WAITLIST
        ).exclude(accounts_available__isnull=True)

        for each_partner in all_partners:
            valid_authorizations = count_valid_authorizations(each_partner.pk)
            total_accounts_available_for_distribution = (
                each_partner.accounts_available - valid_authorizations
            )

            if total_accounts_available_for_distribution > 0:
                each_partner.status = Partner.AVAILABLE
                each_partner.save()
                logger.info(
                    "Partner {name} is unwaitlisted".format(
                        name=each_partner.company_name
                    )
                )
