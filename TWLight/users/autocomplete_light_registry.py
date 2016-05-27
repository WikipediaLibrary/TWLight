import autocomplete_light

from .models import Editor

class EditorAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['^first_name', 'last_name']
    model = Editor

autocomplete_light.register(EditorAutocomplete)
