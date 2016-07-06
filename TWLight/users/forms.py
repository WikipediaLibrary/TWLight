from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Submit

from django.conf import settings
from django.core.urlresolvers import reverse
from django import forms
from django.utils.translation import ugettext as _

from .models import Editor, UserProfile


class EditorUpdateForm(forms.ModelForm):
    class Meta:
        model = Editor
        fields = ['home_wiki', 'contributions']

    def __init__(self, *args, **kwargs):
        """
        This form expects to be instantiated with 'instance=editor' indicating
        the editor to be updated, and will fail otherwise.
        """
        super(EditorUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit(
            'submit',
            _('Update profile'),
            css_class='center-block'))

        editor = self.instance
        self.helper.form_action = reverse('users:editor_update', args=[editor.id])



class SetLanguageForm(forms.Form):
    language = forms.ChoiceField(settings.LANGUAGES)

    def __init__(self, *args, **kwargs):
        super(SetLanguageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.label_class = 'sr-only'



class TermsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['terms_of_use']


    def __init__(self, *args, **kwargs):
        super(TermsForm, self).__init__(*args, **kwargs)

        self.fields['terms_of_use'].label = _("I agree with the terms of use")

        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'

        self.helper.layout = Layout(
            'terms_of_use',
            Submit('submit', 'Submit', css_class='btn btn-default')
        )
