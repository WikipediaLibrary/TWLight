from autocomplete_light import shortcuts as autocomplete_light

from .models import Editor


class EditorAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ["wp_username"]
    model = Editor


autocomplete_light.register(EditorAutocomplete)
