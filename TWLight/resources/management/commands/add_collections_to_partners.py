from django.core.management.base import BaseCommand

from TWLight.resources.models import (
    Partner,
    Stream,
    PartnerLogo,
    Contact,
    Video,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Get Elsevier streams
        elsevier_streams = Stream.objects.filter(
            partner__company_name__contains="Elsevier ScienceDirect"
        )

        # Get Future Science Group streams
        future_science_streams = Stream.objects.filter(
            partner__company_name__contains="Future Science Group"
        )

        # Get RILM streams
        rilm_streams = Stream.objects.filter(
            partner__company_name__contains="Répertoire International de Littérature Musicale (RILM)"
        )

        # Get Springer Nature streams
        springer_nature_streams = Stream.objects.filter(
            partner__company_name__contains="Springer Nature"
        )

        self._turn_stream_to_partner(elsevier_streams)
        self._turn_stream_to_partner(future_science_streams)
        self._turn_stream_to_partner(rilm_streams)
        self._turn_stream_to_partner(springer_nature_streams)

    def _turn_stream_to_partner(self, streams):

        for stream in streams:
            stream_partner_information = {}

            stream_partner_information[
                "company_name"
            ] = "{partner_name} - {stream_name}".format(
                partner_name=stream.partner.company_name, stream_name=stream.name
            )

            if stream.partner.coordinator:
                stream_partner_information["coordinator"] = stream.partner.coordinator

            stream_partner_information["featured"] = stream.partner.featured
            stream_partner_information[
                "company_location"
            ] = stream.partner.company_location
            stream_partner_information["status"] = stream.partner.status
            stream_partner_information[
                "renewals_available"
            ] = stream.partner.renewals_available
            stream_partner_information["accounts_available"] = stream.accounts_available
            stream_partner_information["target_url"] = stream.target_url
            stream_partner_information["terms_of_use"] = stream.partner.terms_of_use
            stream_partner_information[
                "send_instructions"
            ] = stream.partner.send_instructions
            stream_partner_information["user_instructions"] = stream.user_instructions
            stream_partner_information["excerpt_limit"] = stream.partner.excerpt_limit
            stream_partner_information[
                "excerpt_limit_percentage"
            ] = stream.partner.excerpt_limit_percentage
            stream_partner_information[
                "authorization_method"
            ] = stream.authorization_method
            stream_partner_information[
                "mutually_exclusive"
            ] = stream.partner.mutually_exclusive

            stream_partner_information["account_length"] = stream.partner.account_length
            stream_partner_information["new_tags"] = stream.partner.new_tags
            stream_partner_information[
                "registration_url"
            ] = stream.partner.registration_url
            stream_partner_information["real_name"] = stream.partner.real_name
            stream_partner_information[
                "country_of_residence"
            ] = stream.partner.country_of_residence
            stream_partner_information["specific_title"] = stream.partner.specific_title
            stream_partner_information[
                "specific_stream"
            ] = stream.partner.specific_stream
            stream_partner_information["occupation"] = stream.partner.occupation
            stream_partner_information["affiliation"] = stream.partner.affiliation
            stream_partner_information[
                "agreement_with_terms_of_use"
            ] = stream.partner.agreement_with_terms_of_use
            stream_partner_information["account_email"] = stream.partner.account_email
            stream_partner_information[
                "requested_access_duration"
            ] = stream.partner.requested_access_duration

            partner_check = Partner.objects.filter(
                company_name=stream_partner_information["company_name"]
            ).count()

            if partner_check < 1:
                new_partner = Partner.objects.create(**stream_partner_information)

                if stream.languages.all():
                    new_partner.languages.set(stream.languages.all())
                elif stream.partner.languages.all():
                    new_partner.languages.set(stream.partner.languages.all())
