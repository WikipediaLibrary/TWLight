from django.conf import settings
from django import forms
from crispy_forms.helper import FormHelper
from django.utils.translation import get_language


class SetLanguageForm(forms.Form):
    language = forms.ChoiceField(choices=settings.LANGUAGES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields["language"].initial = get_language()
