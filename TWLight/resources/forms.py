from django import forms
from django.utils.translation  import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout

class SuggestForm(forms.Form):
    suggested_company_name = forms.CharField(max_length = 40,)
    description = forms.CharField(widget = forms.Textarea, max_length = 500,)
    company_url = forms.URLField(initial = 'http://')
    
    def __init__(self, *args, **kwargs):
        super(SuggestForm, self).__init__(*args, **kwargs)
        
        self.fields['suggested_company_name'].label = _('Name of the potential partner')
        self.fields['description'].label = _('Description')
        self.fields['company_url'].label = _('Website')
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-7'
        self.helper.layout = Layout(
            'suggested_company_name',
            'description',
            'company_url',
            # Translators: This labels a button which users click to submit their suggestion.
            Submit('submit', _('Submit'), css_class='center-block'),
        )