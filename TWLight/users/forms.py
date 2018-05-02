from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout

from django.conf import settings
from django.core.urlresolvers import reverse
from django import forms
from django.utils.translation import ugettext as _

from .models import Editor, UserProfile
from .groups import get_restricted


class EditorUpdateForm(forms.ModelForm):
    class Meta:
        model = Editor
        fields = ['contributions']

    def __init__(self, *args, **kwargs):
        """
        This form expects to be instantiated with 'instance=editor' indicating
        the editor to be updated, and will fail otherwise.
        """
        super(EditorUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit(
            'submit',
            # Translators: This is the label for a button that users click to update their public information.
            _('Update profile'),
            css_class='center-block'))

        editor = self.instance
        self.helper.form_action = reverse(
            'users:editor_update', args=[editor.id])
        # Translators: This labels a field where users can describe their activity on Wikipedia in a small biography.
        self.fields['contributions'].label = _('Describe your contributions '
            'to Wikipedia: topics edited, et cetera.')
        self.fields['contributions'].help_text = None



class SetLanguageForm(forms.Form):
    language = forms.ChoiceField(settings.LANGUAGES)

    def __init__(self, user, *args, **kwargs):
        super(SetLanguageForm, self).__init__(*args, **kwargs)
        self.fields['language'].initial = user.userprofile.lang
        self.helper = FormHelper()
        self.helper.label_class = 'sr-only'



class RestrictDataForm(forms.Form):
    restricted = forms.BooleanField(required= False)

    def __init__(self, user, *args, **kwargs):
        super(RestrictDataForm, self).__init__(*args, **kwargs)

        # Translators: Labels the button users click to request a restriction on the processing of their data.
        self.fields['restricted'].label = _("Restrict my data")

        restricted = get_restricted()
        user_is_restricted = user in restricted.user_set.all()

        self.fields['restricted'].initial = user_is_restricted

        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'

        self.helper.layout = Layout(
            'data_restricted',
            # Translators: Users click this button to request a restriction on the processing of their data.
            Submit('submit', _('Restrict'), css_class='btn btn-default')
        )



class TermsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['terms_of_use']


    def __init__(self, *args, **kwargs):
        super(TermsForm, self).__init__(*args, **kwargs)

        # Translators: Users must click this button when registering to agree to the website terms of use.
        self.fields['terms_of_use'].label = _("I agree with the terms of use")

        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'

        self.helper.layout = Layout(
            'terms_of_use',
            # Translators: this 'I accept' is referenced in the terms of use and should be translated the same way both places.
            Submit('submit', _('I accept'), css_class='btn btn-default')
        )



class EmailChangeForm(forms.Form):
    email = forms.EmailField()
    use_wp_email = forms.BooleanField(required=False)

    def __init__(self, user, *args, **kwargs):
        super(EmailChangeForm, self).__init__(*args, **kwargs)

        self.fields['email'].label = _('Email')
        # Translators: Users click this button to set their website email address to the one linked to their Wikipedia account.
        self.fields['use_wp_email'].label = _('Use my Wikipedia email address')

        self.fields['email'].initial = user.email
        self.fields['use_wp_email'].initial = user.userprofile.use_wp_email

        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-8'
        self.helper.layout = Layout(
            'email',
            'use_wp_email',
            # Translators: This labels a button which users click to change their email.
            Submit('submit', _('Update email'), css_class='btn btn-default col-md-offset-2')
        )
