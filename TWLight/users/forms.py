from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit, Button, Field

from django.conf import settings
from django.core.urlresolvers import reverse
from django import forms
from django.utils.translation import ugettext as _

from .models import Editor

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

