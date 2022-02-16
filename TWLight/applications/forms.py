"""
This forms.py contains base forms that applications/views.py will use to
generate the actual forms filled in by users in making requests for partner
content.

For usability reasons,  we only want to ask users once for any piece of data,
and we *don't* want to ask them for data that *isn't* required by the partner.

This means that the actual form we present to users must be generated
dynamically; we cannot hardcode it here. What we have here instead is a base
form that takes a dict of required fields, and constructs the form accordingly.
(See the docstring of BaseApplicationForm for the expected dict format.)
"""
from dal import autocomplete
from crispy_forms.bootstrap import InlineField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout,
    Column,
    Row,
    Fieldset,
    Submit,
    BaseInput,
    Div,
    HTML,
)
import logging
import re

from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _

from jsonschema import validate
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from TWLight.resources.models import Partner
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Editor, Authorization

from .helpers import (
    USER_FORM_FIELDS,
    PARTNER_FORM_OPTIONAL_FIELDS,
    PARTNER_FORM_BASE_FIELDS,
    FIELD_TYPES,
    FIELD_LABELS,
    AGREEMENT_WITH_TERMS_OF_USE,
    ACCOUNT_EMAIL,
    get_application_field_params_json_schema,
)
from .models import Application

logger = logging.getLogger(__name__)

coordinators = get_coordinators()


class StylableSubmit(BaseInput):
    """
    The built-in Submit adds classes that don't look right in our context;
    we actually have to create our own input to get around this.
    """

    input_type = "submit"

    def __init__(self, *args, **kwargs):
        self.field_classes = ""
        super().__init__(*args, **kwargs)


class BaseApplicationForm(forms.Form):
    """
    Given a dict of parameters describing the required fields for this
    application, constructs a suitable application form.

    Expected dict format:
        {
            'user': [list, of, required, user, data, fields],
            'partner': [list, of, required, fields, for, partner],
            'partner_id': n
        }

    'user' is mandatory. 'partner' is mandatory. 'partner_id' is mandatory

    See https://django-crispy-forms.readthedocs.org/ for information on form
    layout.
    """

    def __init__(self, *args, **kwargs):
        self._validate_parameters(**kwargs)
        self.field_params = kwargs.pop("field_params")

        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self._initialize_form_helper()

        self.helper.layout = Layout()

        user_data = self.field_params.pop("user")
        self._add_user_data_subform(user_data)

        # Build a partner data section of the form.
        # Since we have popped the user key, only the partner key remains in field_params
        partner_data = self.field_params["partner"]
        partner_id = self.field_params["partner_id"]
        self._add_partner_data_subform(partner_data, partner_id)

        # Make sure to align any checkbox inputs with other field types
        self.helper.filter_by_widget(forms.CheckboxInput).wrap(
            Div, css_class="col-sm-8 offset-sm-4 col-md-9 offset-md-3 apply-tos"
        )

        self.helper.add_input(
            Submit(
                "submit",
                # Translators: Labels the button users click to apply for a partner's resources.
                _("Apply"),
                css_class="mx-auto twl-btn",
            )
        )

    def _get_partner_object(self, partner_id):
        # Verify that it is the ID number of a real partner.
        partner = get_object_or_404(Partner, id=partner_id)

        return partner

    def _validate_parameters(self, **kwargs):
        """
        Ensure that parameters have been passed in and match the format
        specified in the docstring.
        """
        field_params = kwargs["field_params"]
        try:
            validate(
                instance=field_params,
                schema=get_application_field_params_json_schema(),
            )
        except JSONSchemaValidationError:
            raise ValidationError("The field_params dictionary is not valid")

    def _validate_user_data(self, user_data):
        try:
            assert set(user_data) <= set(USER_FORM_FIELDS)
        except AssertionError:
            logger.exception("BaseApplicationForm received invalid user data")
            raise

    def _validate_partner_data(self, partner_data):
        try:
            assert set(partner_data) <= set(PARTNER_FORM_OPTIONAL_FIELDS)

        except AssertionError:
            logger.exception("BaseApplicationForm received invalid partner data")
            raise

    def _initialize_form_helper(self):
        # Add basic styling to the form.
        self.helper.label_class = "col-12 col-sm-4 col-md-3"
        self.helper.field_class = "col-12 col-sm-8 col-md-9"

    def _add_user_data_subform(self, user_data):
        self._validate_user_data(user_data)

        if user_data:
            # Translators: This labels a section of a form where we ask users to enter personal information (such as their country of residence) when making an application.
            user_data_layout = Fieldset(_("About you"))
            for datum in user_data:
                self.fields[datum] = FIELD_TYPES[datum]
                self.fields[datum].label = FIELD_LABELS[datum]
                user_data_layout.append(datum)

            self.helper.layout.append(user_data_layout)
            # fmt: off
            # Translators: This note appears in a section of a form where we ask users to enter info (like country of residence) when applying for resource access.
            disclaimer_html = _("<p><small><i>Your personal data will be processed according to our <a class='twl-links' href='{terms_url}'> privacy policy</a>.</i></small></p>").format(
                terms_url=reverse("terms")
            )
            # fmt: on
            self.helper.layout.append(HTML(disclaimer_html))

    def _add_partner_data_subform(self, partner_data, partner_id):
        partner_object = self._get_partner_object(partner_id)
        partner_layout = Fieldset(
            # Translators: This is the title of the application form page, where users enter information required for the application. It lets the user know which partner application they are entering data for. {partner}
            _("Your application to {partner}").format(partner=partner_object)
        )

        self._validate_partner_data(partner_data)

        # partner_data lists the optional fields required by that partner;
        # base fields should be in the form for all partners.
        all_partner_data = partner_data + PARTNER_FORM_BASE_FIELDS

        if all_partner_data:
            for datum in all_partner_data:
                # This will yield fields with names like 'partner_occupation'
                field_name = "partner_{datum}".format(datum=datum)
                self.fields[field_name] = FIELD_TYPES[datum]
                self.fields[field_name].label = FIELD_LABELS[datum]

                if datum == AGREEMENT_WITH_TERMS_OF_USE:
                    # Make sure that, if the partner requires agreement with
                    # terms of use, that link is provided inline.
                    help_text = '<a href="{url}">{url}</a>'.format(
                        url=partner_object.terms_of_use
                    )
                    self.fields[field_name].help_text = help_text

                if datum == ACCOUNT_EMAIL:
                    # If partner requires pre-registration, make sure users
                    # get a link where they can sign up.
                    url = '<a href="{url}">{url}</a>'.format(
                        url=partner_object.registration_url
                    )
                    # Translators: For some applications, users must register at another website before finishing the application form, and must then enter their email address used when registering. Don't translate {url}.
                    help_text = _("You must register at {url} before applying.").format(
                        url=url
                    )
                    self.fields[field_name].help_text = help_text

                partner_layout.append(field_name)

            self.helper.layout.append(partner_layout)


class ApplicationAutocomplete(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["editor", "partner"]
        widgets = {
            "editor": autocomplete.ModelSelect2(
                url="applications:editor_autocomplete",
                attrs={"data-placeholder": "Username"},
            ),
            "partner": autocomplete.ModelSelect2(
                url="applications:partner_autocomplete",
                attrs={"data-placeholder": "Partner"},
            ),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make sure that we aren't leaking info via our form choices.
        if user.is_superuser:
            self.fields["editor"].queryset = Editor.objects.all().order_by(
                "wp_username"
            )

            self.fields["partner"].queryset = Partner.objects.all().order_by(
                "company_name"
            )

        elif coordinators in user.groups.all():
            self.fields["editor"].queryset = Editor.objects.filter(
                applications__partner__coordinator__pk=user.pk
            ).order_by("wp_username")

            self.fields["partner"].queryset = Partner.objects.filter(
                coordinator__pk=user.pk
            ).order_by("company_name")

        # Prettify.
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.label_class = "sr-only"
        self.helper.layout = Layout(
            Row(
                Column("editor", css_class="col-lg-6 px-sm-3 col-sm-8 mx-sm-1"),
                css_class="form-group my-1",
            ),
            Row(
                Column("partner", css_class="col-lg-6 px-sm-3 col-sm-8 mx-sm-1"),
                css_class="form-group my-1",
            ),
            Row(
                Submit("submit", "Filter", css_class="btn btn-default mx-sm-1"),
                css_class="form-group my-1 px-lg-3 col-sm-3 col-xs-4 px-xs-2",
            ),
        )

        # Required on the model, but optional for autocomplete, so override
        # the default.
        self.fields["editor"].required = False
        self.fields["partner"].required = False

        # Internationalize user-visible labels. These will appear inline as
        # placeholders.
        # Translators: Label of the field where coordinators can enter the username of a user
        self.fields["editor"].label = _("Username")
        # Translators: Label of the field where coordinators can enter the name of a partner
        self.fields["partner"].label = _("Partner name")


class RenewalForm(forms.Form):
    def __init__(self, *args, **kwargs):
        try:
            self.field_params = kwargs.pop("field_params")
        except KeyError:
            logger.exception(
                "Tried to instantiate a RenewalForm but did not have field_params"
            )
            raise
        super(RenewalForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        # Translators: This will be the title of the page where users will have to confirm their renewal request of an application.
        fieldset = Fieldset(_("Renewal confirmation"))

        account_email = False
        if (
            "account_email" in self.field_params
            and self.field_params["account_email"] is not None
        ):
            self.fields["account_email"] = forms.EmailField(
                initial=self.field_params["account_email"]
            )
            account_email = True
        elif "account_email" in self.field_params:
            self.fields["account_email"] = forms.EmailField()
            account_email = True
        if account_email:
            # fmt: off
            # Translators: This labels an email field where users will be asked to enter their emails as part of the application renewal confirmation.
            self.fields["account_email"].label = _("The email for your account on the partner's website")
            # fmt: on
            fieldset.append("account_email")

        if "requested_access_duration" in self.field_params:
            self.fields["requested_access_duration"] = forms.ChoiceField(
                choices=Application.REQUESTED_ACCESS_DURATION_CHOICES
            )
            # fmt: off
            # Translators: This labels a choice field where users will have to select the number of months they wish to have their access for as part of the application renewal confirmation.
            self.fields["requested_access_duration"].label = _("The number of months you wish to have this access for before renewal is required")
            # fmt: on
            fieldset.append("requested_access_duration")

        self.fields["return_url"] = forms.CharField(
            widget=forms.HiddenInput, max_length=70
        )
        self.fields["return_url"].initial = self.field_params["return_url"]
        fieldset.append("return_url")

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.label_class = "col-lg-3"
        self.helper.field_class = "col-lg-4"

        self.helper.layout = Layout()
        self.helper.layout.append(fieldset)
