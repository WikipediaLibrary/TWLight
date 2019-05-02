from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.applications.helpers import get_active_authorizations
from TWLight.resources.models import Partner

class Command(BaseCommand):
    help = "Un-waitlists proxy partners having atleast one inactive authorization."

    def handle(self, *args, **options):
        all_partners = Partner.objects.filter(authorization_method=Partner.PROXY, status=Partner.WAITLIST).exclude(specific_stream=True, accounts_available__isnull=True)
        
        for each_partner in all_partners:
            active_authorizations = get_active_authorizations(each_partner.pk)
            total_accounts_available_for_distribution = each_partner.accounts_available - active_authorizations
            
            if total_accounts_available_for_distribution > 0:
                each_partner.status = Partner.AVAILABLE
                each_partner.save()
                print('{name}\'s been unwaitlisted'.format(name=each_partner.company_name))
