import autocomplete_light

from .models import Partner

class PersonAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['company_name']
    model = Partner

autocomplete_light.register(PersonAutocomplete)
