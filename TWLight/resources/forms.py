from django import forms
from django.utils.translation import gettext_lazy as _
from TWLight.resources.models import Suggestion

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout


class SuggestionForm(forms.Form):
    suggested_company_name = forms.CharField(max_length=40)
    description = forms.CharField(widget=forms.Textarea, max_length=500)
    company_url = forms.URLField(initial="http://")
    next = forms.CharField(widget=forms.HiddenInput, max_length=40)

    def __init__(self, *args, **kwargs):
        super(SuggestionForm, self).__init__(*args, **kwargs)
        # Translators: This labels a textfield where users can enter the name of the potential partner they'll suggest
        self.fields["suggested_company_name"].label = _("Name of the potential partner")
        # Translators: This labels a textfield where users can enter the description of the potential partner they'll suggest
        self.fields["description"].label = _("Description")
        # Translators: This labels a textfield where users can enter the website URL of the potential partner they'll suggest
        self.fields["company_url"].label = _("Website")
        # @TODO: This sort of gets repeated in PartnerSuggestionView.
        # We could probably be factored out to a common place for DRYness.
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-3"
        self.helper.field_class = "col-lg-12"
        self.helper.layout = Layout(
            "suggested_company_name",
            "description",
            "company_url",
            "next",
            # Translators: This labels a button which users click to submit their suggestion.
            Submit("submit", _("Submit"), css_class="twl-btn"),
        )


class SuggestionMergeForm(forms.Form):

    suggestions_to_merge = forms.ModelMultipleChoiceField(
        queryset=Suggestion.objects.all()
    )
    suggestions_merged_into = forms.ModelChoiceField(queryset=Suggestion.objects.all())

    def __init__(self, *args, **kwargs):
        super(SuggestionMergeForm, self).__init__(*args, **kwargs)
        # Translators: This labels a multiple choice field to choose the suggestions to merge
        self.fields["suggestions_to_merge"].label = _("Merged suggestions")
        # Translators: This labels a choiceField where users can enter the suggestion to merge into
        self.fields["suggestions_merged_into"].label = _("Merge suggestions into")
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "suggestions_to_merge",
            "suggestions_merged_into",
            # Translators: This labels a button which users click to merge suggestions.
            Submit("submit", _("Submit"), css_class="twl-btn"),
        )
