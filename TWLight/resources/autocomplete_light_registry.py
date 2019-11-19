from autocomplete_light import shortcuts as autocomplete_light

from .models import Partner


class PartnerAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ["company_name"]
    model = Partner

    # Without this line, the autocomplete apparently supplies all Partners,
    # even the NOT_AVAILABLE ones excluded by the default queryset, which causes
    # form submission to fail with DoesNotExist when people filter for an
    # unavailable partner. As this autocomplete is presented in a context where
    # NOT_AVAILABLE partners aren't allowed, let's filter them out. If we need
    # an autocomplete over all possible partners, create and register a
    # separate one and use that in other contexts.
    choices = Partner.objects.all()


autocomplete_light.register(PartnerAutocomplete)
