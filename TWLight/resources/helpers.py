def check_for_target_url_duplication_and_generate_error_message(
    self, partner=False, stream=False
):
    """
    Filter for partners/streams (PROXY and BUNDLE) where the
    target_url is the same as self. On filtering, if we have
    a non-zero number of matches, we generate the appropriate
    error message to be shown to the staff.

    :param self:
    :param partner:
    :param stream:
    :return:
    """
    from TWLight.resources.models import Partner, Stream

    duplicate_target_url_partners = Partner.objects.filter(
        authorization_method__in=[Partner.PROXY, Partner.BUNDLE],
        target_url=self.target_url,
    ).values_list("company_name", flat=True)
    # Exclude self from the filtered partner list, if the operation
    # is performed on Partners.
    if partner:
        duplicate_target_url_partners = duplicate_target_url_partners.exclude(
            pk=self.pk
        )

    duplicate_target_url_streams = Stream.objects.filter(
        authorization_method__in=[Partner.PROXY, Partner.BUNDLE],
        target_url=self.target_url,
    ).values_list("name", flat=True)
    # Exclude self from the filtered stream list, if the operation
    # is performed on Streams.
    if stream:
        duplicate_target_url_streams = duplicate_target_url_streams.exclude(pk=self.pk)

    partner_duplicates_count = duplicate_target_url_partners.count()
    stream_duplicates_count = duplicate_target_url_streams.count()

    if partner_duplicates_count != 0 or stream_duplicates_count != 0:
        validation_error_msg = (
            "No two or more partners/streams can have the same target url. "
            "The following partner(s)/stream(s) have the same target url: "
        )
        validation_error_msg_partners = "None"
        validation_error_msg_streams = "None"
        if partner_duplicates_count > 1:
            validation_error_msg_partners = ", ".join(duplicate_target_url_partners)
        elif partner_duplicates_count == 1:
            validation_error_msg_partners = duplicate_target_url_partners[0]
        if stream_duplicates_count > 1:
            validation_error_msg_streams = ", ".join(duplicate_target_url_streams)
        elif stream_duplicates_count == 1:
            validation_error_msg_streams = duplicate_target_url_streams[0]

        return (
            validation_error_msg
            + " Partner(s): "
            + validation_error_msg_partners
            + ". Stream(s): "
            + validation_error_msg_streams
            + "."
        )

    return None


def get_json_schema():
    """
    JSON Schema for partner description translations
    """
    from TWLight.resources.models import Partner

    no_of_partners = Partner.objects.count()
    no_of_possible_descriptions = no_of_partners * 2

    JSON_SCHEMA_PARTNER_DESCRIPTION = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "maxItems": no_of_possible_descriptions,
    }

    return JSON_SCHEMA_PARTNER_DESCRIPTION
