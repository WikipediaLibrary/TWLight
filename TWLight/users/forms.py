from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Column, Row

from django.conf import settings

from django.urls import reverse
from django import forms
from django.utils.translation import gettext as _

from .helpers.validation import validate_partners, validate_authorizer
from .models import Editor, UserProfile, Authorization
from .groups import get_restricted


class EditorUpdateForm(forms.ModelForm):
    """
    Defines form accessed from the user profile page, whereby users can update
    their contributions information.
    """

    class Meta:
        model = Editor
        fields = ["contributions"]

    def __init__(self, *args, **kwargs):
        """
        This form expects to be instantiated with 'instance=editor' indicating
        the editor to be updated, and will fail otherwise.
        """
        super(EditorUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(
            Submit(
                "submit",
                # Translators: This is the label for a button that users click to update their public information.
                _("Update profile"),
                css_class="twl-btn",
            )
        )

        editor = self.instance
        self.helper.form_action = reverse("users:editor_update", args=[editor.id])
        # fmt: off
        # Translators: This labels a field where users can describe their activity on Wikipedia in a small biography.
        self.fields["contributions"].label = _("Describe your contributions " "to Wikipedia: topics edited, et cetera.")
        # fmt: on
        self.fields["contributions"].help_text = None


class AuthorizationAdminForm(forms.ModelForm):
    """
    This override only exists to run custom validation.
    """

    class Meta:
        model = Authorization
        fields = "__all__"

    def clean_partners(self):
        validate_partners(self.cleaned_data["partners"])
        return self.cleaned_data["partners"]

    def clean_authorizer(self):
        validate_authorizer(self.cleaned_data["authorizer"])
        return self.cleaned_data["authorizer"]


class SetLanguageForm(forms.Form):
    """
    Defines form used by users to change their interface language.
    """

    language = forms.ChoiceField(choices=settings.LANGUAGES)

    def __init__(self, user, *args, **kwargs):
        super(SetLanguageForm, self).__init__(*args, **kwargs)
        self.fields["language"].initial = user.userprofile.lang
        self.helper = FormHelper()
        self.helper.label_class = "sr-only"


class UserEmailForm(forms.Form):
    """
    Defines form used by users to opt in or out of emails notifying them that
    one of their collections is up for renewal soon.
    """

    send_renewal_notices = forms.BooleanField(required=False)

    def __init__(self, user, *args, **kwargs):
        super(UserEmailForm, self).__init__(*args, **kwargs)
        self.fields["send_renewal_notices"].initial = (
            user.userprofile.send_renewal_notices
        )
        self.fields[
            "send_renewal_notices"
            # Translators: In the preferences section (Emails) of a user profile, this text labels the checkbox users can (un)click to change if they wish to receive account renewal notices or not.
        ].label = _("Send renewal notices")


class CoordinatorEmailForm(forms.Form):
    """
    Defines form available to coordinators, used to configure email
    preferences for various available reminder emails.
    """

    send_pending_application_reminders = forms.BooleanField(required=False)
    send_discussion_application_reminders = forms.BooleanField(required=False)
    send_approved_application_reminders = forms.BooleanField(required=False)

    def __init__(self, user, *args, **kwargs):
        super(CoordinatorEmailForm, self).__init__(*args, **kwargs)
        # We default to the values from the user's userprofile on
        # page (Profile) load.
        self.fields["send_pending_application_reminders"].initial = (
            user.userprofile.pending_app_reminders
        )
        self.fields[
            "send_pending_application_reminders"
            # Translators: In the preferences section (Emails) of a user profile, this text labels the checkbox coordinators can (un)click to change if they wish to receive pending application reminders or not.
        ].label = _("Send pending application reminders")

        self.fields["send_discussion_application_reminders"].initial = (
            user.userprofile.discussion_app_reminders
        )
        self.fields[
            "send_discussion_application_reminders"
            # Translators: In the preferences section (Emails) of a user profile, this text labels the checkbox coordinators can (un)click to change if they wish to receive application reminders that are under discussion or not.
        ].label = _("Send discussion application reminders")

        self.fields["send_approved_application_reminders"].initial = (
            user.userprofile.approved_app_reminders
        )
        self.fields[
            "send_approved_application_reminders"
            # Translators: In the preferences section (Emails) of a user profile, this text labels the checkbox coordinators can (un)click to change if they wish to receive approved application reminders or not.
        ].label = _("Send approved application reminders")


class RestrictDataForm(forms.Form):
    """
    Defines the form whereby users can opt-in to have their data processing
    restricted.
    """

    restricted = forms.BooleanField(required=False)

    def __init__(self, user, *args, **kwargs):
        super(RestrictDataForm, self).__init__(*args, **kwargs)

        # Translators: Labels the button users click to request a restriction on the processing of their data.
        self.fields["restricted"].label = _("Restrict my data")

        restricted = get_restricted()
        user_is_restricted = user in restricted.user_set.all()

        self.fields["restricted"].initial = user_is_restricted

        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.field_template = "bootstrap4/layout/inline_field.html"


class TermsForm(forms.ModelForm):
    """
    Defines the form used by users to agree to the library's terms of use.
    """

    class Meta:
        model = UserProfile
        fields = ["terms_of_use"]

    def __init__(self, user_profile, *args, **kwargs):
        super(TermsForm, self).__init__(*args, **kwargs)

        # Translators: Users must click this button when registering to agree to the website terms of use.
        self.fields["terms_of_use"].label = _("I agree with the terms of use")
        if user_profile:
            self.fields["terms_of_use"].initial = user_profile.terms_of_use
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.field_template = "bootstrap4/layout/inline_field.html"
        # fmt: off
        # Translators: This text explains how to disagree to the site's terms of use and the restrictions that will come into effect when users disagree to the terms of use.
        self.fields["terms_of_use"].help_text = _("By unchecking this box and clicking “Update” you may explore the site, but you will not be able to apply for access to materials or evaluate applications unless you agree with the terms of use.")
        # fmt: on

        self.helper.layout = Layout(
            "terms_of_use",
            # Translators: this 'Submit' is referenced in the terms of use and should be translated the same way both places.
            Submit("submit", _("Submit"), css_class="btn twl-btn"),
        )


class EmailChangeForm(forms.Form):
    """
    Defines the form used by users to change the email address associated with
    their account, or to automatically fetch their Wikipedia email.
    """

    email = forms.EmailField(required=False)
    use_wp_email = forms.BooleanField(required=False)

    def __init__(self, user, *args, **kwargs):
        super(EmailChangeForm, self).__init__(*args, **kwargs)

        # Translators: Labels the field where the user's email is displayed.
        self.fields["email"].label = _("Email")
        # fmt: off
        # Translators: Users click this button to set their website email address to the one linked to their Wikipedia account.
        self.fields["use_wp_email"].label = _("Use my Wikipedia email address "
            "(will be updated the next time you login)."
        )
        # fmt: on

        self.fields["email"].initial = user.email
        self.fields["use_wp_email"].initial = user.userprofile.use_wp_email

        self.helper = FormHelper()
        self.helper.form_class = "mx-auto w-75 px-5"
        self.helper.label_class = "font-weight-bold w-25 d-inline"
        self.helper.layout = Layout(
            Row(
                Column("email", css_class="form-group w-100 d-inline"),
            ),
            Row(
                Column("use_wp_email", css_class="form-group w-100"),
            ),
            Submit(
                "submit",
                # Translators: This labels a button which users click to change their email.
                _("Update email"),
                css_class="twl-btn",
            ),
        )
