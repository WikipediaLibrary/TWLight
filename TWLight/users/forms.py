from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django.core.urlresolvers import reverse
from django.forms import ModelForm
from django.utils.translation import ugettext as _

from .models import Editor

class EditorUpdateForm(ModelForm):
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
