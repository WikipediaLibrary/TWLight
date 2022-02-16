from django import forms
from django.utils.translation import gettext_lazy as _

from TWLight.resources.models import Partner

from .models import Application
from ..users.helpers.authorizations import get_valid_partner_authorizations

"""
Lists and characterizes the types of information that partners can require as
part of access grants. See full comment at end of file and docs at
https://github.com/WikipediaLibrary/TWLight/blob/master/docs/developer.md#changing-the-data-collected-on-application-forms
"""

"""
Harvestable from user profile:
    Username (all partnerships)
    Email (all partnerships)

Required/nonharvestable:

Optional/universal:
    Real name (many partners)
    Country of residence (Pelican, Numerique)
    Occupation (Elsevier)
    Affiliation (Elsevier)

Optional/unique:
    Questions/comments/concerns (free-text, all partnerships)
    Title requested (McFarland, Pelican)
    Agreement with Terms of Use (RSUK)
"""

# ~~~~~ Named constants ~~~~~ #
REAL_NAME = "real_name"
COUNTRY_OF_RESIDENCE = "country_of_residence"
OCCUPATION = "occupation"
AFFILIATION = "affiliation"
PARTNER = "partner"
RATIONALE = "rationale"
SPECIFIC_TITLE = "specific_title"
COMMENTS = "comments"
AGREEMENT_WITH_TERMS_OF_USE = "agreement_with_terms_of_use"
ACCOUNT_EMAIL = "account_email"
REQUESTED_ACCESS_DURATION = "requested_access_duration"


# ~~~~ Basic field names ~~~~ #
USER_FORM_FIELDS = [REAL_NAME, COUNTRY_OF_RESIDENCE, OCCUPATION, AFFILIATION]

# These fields are displayed for all partners.
PARTNER_FORM_BASE_FIELDS = [RATIONALE, COMMENTS]

# These fields are displayed only when a specific partner requires that
# information.
PARTNER_FORM_OPTIONAL_FIELDS = [
    SPECIFIC_TITLE,
    AGREEMENT_WITH_TERMS_OF_USE,
    ACCOUNT_EMAIL,
    REQUESTED_ACCESS_DURATION,
]


# ~~~~ Field information ~~~~ #
FIELD_TYPES = {
    REAL_NAME: forms.CharField(max_length=128),
    COUNTRY_OF_RESIDENCE: forms.CharField(max_length=128),
    OCCUPATION: forms.CharField(max_length=128),
    AFFILIATION: forms.CharField(max_length=128),
    PARTNER: forms.ModelChoiceField(
        queryset=Partner.objects.all(), widget=forms.HiddenInput
    ),
    RATIONALE: forms.CharField(widget=forms.Textarea),
    SPECIFIC_TITLE: forms.CharField(max_length=128),
    COMMENTS: forms.CharField(widget=forms.Textarea, required=False),
    AGREEMENT_WITH_TERMS_OF_USE: forms.BooleanField(),
    ACCOUNT_EMAIL: forms.EmailField(),
    REQUESTED_ACCESS_DURATION: forms.ChoiceField(
        choices=Application.REQUESTED_ACCESS_DURATION_CHOICES
    ),
}

FIELD_LABELS = {
    # Translators: When filling out an application, users may need to specify their name
    REAL_NAME: _("Your real name"),
    # Translators: When filling out an application, users may need to specify the country in which they currently live
    COUNTRY_OF_RESIDENCE: _("Your country of residence"),
    # Translators: When filling out an application, users may need to specify their current occupation
    OCCUPATION: _("Your occupation"),
    # Translators: When filling out an application, users may need to specify if they are affiliated with an institution (e.g. a university)
    AFFILIATION: _("Your institutional affiliation"),
    # Translators: When filling out an application, this labels the name of the publisher or database the user is applying to
    PARTNER: _("Partner name"),
    # Translators: When filling out an application, users must provide an explanation of why these resources would be useful to them
    RATIONALE: _("Why do you want access to this resource?"),
    # Translators: When filling out an application, users may need to specify a particular book they want access to
    SPECIFIC_TITLE: _("Which book do you want?"),
    # Translators: When filling out an application, users are given a text box where they can include any extra relevant information
    COMMENTS: _("Anything else you want to say"),
    # Translators: When filling out an application, users may be required to check a box to say they agree with the website's Terms of Use document, which is linked
    AGREEMENT_WITH_TERMS_OF_USE: _("You must agree with the partner's terms of use"),
    # Translators: When filling out an application, users may be required to enter an email they have used to register on the partner's website.
    ACCOUNT_EMAIL: _("The email for your account on the partner's website"),
    # fmt: off
    # Translators: When filling out an application, users may be required to enter the length of the account (expiry) they wish to have for proxy partners.
    REQUESTED_ACCESS_DURATION: _("The number of months you wish to have this access for before renewal is required"),
    # fmt: on
}

SEND_DATA_FIELD_LABELS = {
    # Translators: When sending application data to partners, this is the text labelling a user's real name
    REAL_NAME: _("Real name"),
    # Translators: When sending application data to partners, this is the text labelling a user's country of residence
    COUNTRY_OF_RESIDENCE: _("Country of residence"),
    # Translators: When sending application data to partners, this is the text labelling a user's occupation
    OCCUPATION: _("Occupation"),
    # Translators: When sending application data to partners, this is the text labelling a user's affiliation
    AFFILIATION: _("Affiliation"),
    # Translators: When sending application data to partners, this is the text labelling the specific title (e.g. a particular book) a user requested
    SPECIFIC_TITLE: _("Title requested"),
    # Translators: When sending application data to partners, this is the text labelling whether a user agreed with the partner's Terms of Use
    AGREEMENT_WITH_TERMS_OF_USE: _("Agreed with terms of use"),
    # Translators: When sending application data to partners, this is the text labelling the user's email on the partner's website, if they had to register in advance of applying.
    ACCOUNT_EMAIL: _("Account email"),
}


def get_output_for_application(app):
    """
    This collates the data that we need to send to publishers for a given
    application. Since different publishers require different data and we don't
    want to share personal data where not required, we construct this function
    to fetch only the required data rather than displaying all of Application
    plus Editor in the front end.
    """

    # Translators: This labels a user's email address on a form for account coordinators
    output = {_("Email"): {"label": "Email", "data": app.editor.user.email}}

    for field in PARTNER_FORM_OPTIONAL_FIELDS:
        # Since we directly mark applications made to proxy partners as 'sent', this function wouldn't be invoked.
        # But for tests, and in the off chance we stumble into this function for when requested_access_duration is true
        # and the partner isn't proxy, we don't want the data to be sent to partners, which is why it's not part
        # of the SEND_DATA_FIELD_LABELS.
        if field == "requested_access_duration":
            break
        if getattr(app.partner, field):  # Will be True if required by Partner.
            field_label = SEND_DATA_FIELD_LABELS[field]
            output[field] = {"label": field_label, "data": getattr(app, field)}

    for field in USER_FORM_FIELDS:
        if getattr(app.partner, field):  # Will be True if required by Partner.
            field_label = SEND_DATA_FIELD_LABELS[field]
            output[field] = {"label": field_label, "data": getattr(app.editor, field)}

    return output


def count_valid_authorizations(partner_pk):
    """
    Retrieves the numbers of valid authorizations using the
    get_valid_partner_authorizations() method above.
    """
    return get_valid_partner_authorizations(partner_pk).count()


def get_accounts_available(app):
    """
    Because we allow number of accounts available on the partner level,
    we base our calculations on the partner level.
    """
    if app.partner.accounts_available is not None:
        valid_authorizations = count_valid_authorizations(app.partner)
        return app.partner.accounts_available - valid_authorizations


def is_proxy_and_application_approved(status, app):
    if (
        app.partner.authorization_method == Partner.PROXY
        and status == Application.APPROVED
    ):
        return True
    else:
        return False


def more_applications_than_accounts_available(app):
    total_accounts_available_for_distribution = get_accounts_available(app)
    if total_accounts_available_for_distribution is not None and app.status in [
        Application.PENDING,
        Application.QUESTION,
    ]:
        total_pending_apps = Application.objects.filter(
            partner=app.partner, status__in=[Application.PENDING, Application.QUESTION]
        )
        if (
            app.partner.status != Partner.WAITLIST
            and total_accounts_available_for_distribution > 0
            and total_accounts_available_for_distribution - total_pending_apps.count()
            < 0
        ):
            return True
    return False


def get_application_field_params_json_schema():
    """
    JSON Schema for the field_params object that will be used to create the form
    for the application
    """
    JSON_SCHEMA_FIELD_PARAMS = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "partner": {
                "$id": "#/properties/partner",
                "type": "array",
                "items": {
                    "$id": "#/properties/partner/items",
                    "type": "string",
                    "examples": ["specific_title", "agreement_with_terms_of_use"],
                },
            },
            "partner_id": {
                "$id": "#/properties/partner_id",
                "type": "number",
            },
            "user": {
                "$id": "#/properties/user",
                "type": "object",
            },
        },
        "additionalProperties": False,
        "required": ["partner", "partner_id", "user"],
    }

    return JSON_SCHEMA_FIELD_PARAMS


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

"""
Information comes in three types:
1) Information required for all access grants. (Example: wikipedia username)
2) Information that only some partners require, but which will be the same for
   all partners in any given application. (Example: country of residence)
3) Information that only some partners require, and that may differ for
   different partners. (Example: rationale for resource request)

These facts about required/optional status are used to generate application
forms. In particular, we can generate application forms which impose the
smallest possible data entry burden on users by:
* omitting optional fields if they aren't required by any of the requested
  partners;
* asking for optional information only once per application, rather than once
  per partner, if it will be the same for all partners.

Facts related to this file are hardcoded in three other places in the database:

1) In TWLight.resources.models.Partner, which tracks whether a given partner
   requires the optional information;
2) In TWLight.applications.forms.Application, which has fields for all
   possible partner-specific information (though any given application instance
   may leave optional fields blank).
3) In TWLight.users.models.Editor, which records user data.

Why this hardcoding? Well, having defined database models lets us take advantage
of an awful lot of Django machinery. Also, dynamically generating everything on
the fly might be slow and lead to hard-to-read code.

applications.tests checks to make sure that these three sources are in agreement
about the optional data fields available: both their names and their types. It
also checks that the constructed application form fields match those types.
"""
