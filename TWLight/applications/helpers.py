from django import forms
from django.utils.translation import ugettext as _

from TWLight.resources.models import Partner, Stream

from .models import Application

"""
Lists and characterizes the types of information that partners can require as
part of access grants. See full comment at end of file.
"""

"""
Harvestable from user profile:
    Username (all partnerships)
    Email (all partnerships)
    Projects user is active on (all partnerships)
    Call for volunteers (as needed - checkbox "I'm interested")

        Perhaps invite them to review/update their user profile as part of
        application process.

        Make sure to communicate to them what info will be shared with
        coordinators and what to expect...

Required/nonharvestable:

Optional/universal:
    Real name (many partners)
    Country of residence (Pelican, Numerique)
    Occupation (Elsevier)
    Affiliation (Elsevier)

Optional/unique:
    Questions/comments/concerns (free-text, all partnerships)
    Title requested (McFarland, Pelican)
    Stream requested (OUP, T&F, Elsevier)
    Agreement with Terms of Use (RSUK)
"""

# ~~~~~ Named constants ~~~~~ #
REAL_NAME = 'real_name'
COUNTRY_OF_RESIDENCE = 'country_of_residence'
OCCUPATION = 'occupation'
AFFILIATION = 'affiliation'
PARTNER = 'partner'
RATIONALE = 'rationale'
SPECIFIC_STREAM = 'specific_stream'
SPECIFIC_TITLE = 'specific_title'
COMMENTS = 'comments'
AGREEMENT_WITH_TERMS_OF_USE = 'agreement_with_terms_of_use'
ACCOUNT_EMAIL = 'account_email'
PROXY_ACCOUNT_LENGTH = 'proxy_account_length'
HIDDEN = 'hidden'


# ~~~~ Basic field names ~~~~ #
USER_FORM_FIELDS = [REAL_NAME, COUNTRY_OF_RESIDENCE, OCCUPATION,
                    AFFILIATION]

# These fields are displayed for all partners.
PARTNER_FORM_BASE_FIELDS = [RATIONALE, COMMENTS, HIDDEN]

# These fields are displayed only when a specific partner requires that
# information.
PARTNER_FORM_OPTIONAL_FIELDS = [SPECIFIC_STREAM, SPECIFIC_TITLE,
                                AGREEMENT_WITH_TERMS_OF_USE, ACCOUNT_EMAIL, PROXY_ACCOUNT_LENGTH]


# ~~~~ Field information ~~~~ #
FIELD_TYPES = {
    REAL_NAME: forms.CharField(max_length=128),
    COUNTRY_OF_RESIDENCE: forms.CharField(max_length=128),
    OCCUPATION: forms.CharField(max_length=128),
    AFFILIATION: forms.CharField(max_length=128),
    PARTNER: forms.ModelChoiceField(
        queryset=Partner.objects.all(),
        widget=forms.HiddenInput),
    RATIONALE: forms.CharField(widget=forms.Textarea),
    SPECIFIC_STREAM: forms.ModelChoiceField(queryset=Stream.objects.all()),
    SPECIFIC_TITLE: forms.CharField(max_length=128),
    COMMENTS: forms.CharField(widget=forms.Textarea, required=False),
    AGREEMENT_WITH_TERMS_OF_USE: forms.BooleanField(),
    ACCOUNT_EMAIL: forms.EmailField(),
    PROXY_ACCOUNT_LENGTH: forms.ChoiceField(choices=Application.PROXY_ACCOUNT_LENGTH_CHOICES),
    HIDDEN: forms.BooleanField(required=False)
}

FIELD_LABELS = {
    # Translators: When filling out an application, users may need to specify their name
    REAL_NAME: _('Your real name'),
    # Translators: When filling out an application, users may need to specify the country in which they currently live
    COUNTRY_OF_RESIDENCE: _('Your country of residence'),
    # Translators: When filling out an application, users may need to specify their current occupation
    OCCUPATION: _('Your occupation'),
    # Translators: When filling out an application, users may need to specify if they are affiliated with an institution (e.g. a university)
    AFFILIATION: _('Your institutional affiliation'),
    # Translators: When filling out an application, this labels the name of the publisher or database the user is applying to
    PARTNER: _('Partner name'),
    # Translators: When filling out an application, users must provide an explanation of why these resources would be useful to them
    RATIONALE: _('Why do you want access to this resource?'),
    # Translators: When filling out an application, users may need to specify a particular collection of resources they want access to
    SPECIFIC_STREAM: _('Which collection do you want?'),
    # Translators: When filling out an application, users may need to specify a particular book they want access to
    SPECIFIC_TITLE: _('Which book do you want?'),
    # Translators: When filling out an application, users are given a text box where they can include any extra relevant information
    COMMENTS: _('Anything else you want to say'),
    # Translators: When filling out an application, users may be required to check a box to say they agree with the website's Terms of Use document, which is linked
    AGREEMENT_WITH_TERMS_OF_USE: _("You must agree with the partner's terms of use"),
    # Translators: When filling out an application, users may be required to enter an email they have used to register on the partner's website.
    ACCOUNT_EMAIL: _("The email for your account on the partner's website"),
    # Translators: When filling out an application, users may be required to enter the length of the account (expiry) they wish to have for proxy partners.
    PROXY_ACCOUNT_LENGTH: _("The number of months you wish to have this access for before renewal is required"),
    # Translators: When filling out an application, this text labels a checkbox that hides this application from the website's 'latest activity' timeline.
    HIDDEN: _("Check this box if you would prefer to hide your application from the 'latest activity' timeline.")
}

SEND_DATA_FIELD_LABELS = {
    # Translators: When sending application data to partners, this is the text labelling a user's real name
    REAL_NAME: _('Real name'),
    # Translators: When sending application data to partners, this is the text labelling a user's country of residence
    COUNTRY_OF_RESIDENCE: _('Country of residence'),
    # Translators: When sending application data to partners, this is the text labelling a user's occupation
    OCCUPATION: _('Occupation'),
    # Translators: When sending application data to partners, this is the text labelling a user's affiliation
    AFFILIATION: _('Affiliation'),
    # Translators: When sending application data to partners, this is the text labelling the stream/collection a user requested
    SPECIFIC_STREAM: _('Stream requested'),
    # Translators: When sending application data to partners, this is the text labelling the specific title (e.g. a particular book) a user requested
    SPECIFIC_TITLE: _('Title requested'),
    # Translators: When sending application data to partners, this is the text labelling whether a user agreed with the partner's Terms of Use
    AGREEMENT_WITH_TERMS_OF_USE: _('Agreed with terms of use'),
    # Translators: When sending application data to partners, this is the text labelling the user's email on the partner's website, if they had to register in advance of applying.
    ACCOUNT_EMAIL: _('Account email'),
}


def get_output_for_application(app):
    """
    This collates the data that we need to send to publishers for a given
    application. Since different publishers require different data and we don't
    want to share personal data where not required, we construct this function
    to fetch only the required data rather than displaying all of Application
    plus Editor in the front end.
    """
    output = {}
    # Translators: This labels a user's email address on a form for account coordinators
    output[_('Email')] = {'label': 'Email', 'data': app.editor.user.email}

    for field in PARTNER_FORM_OPTIONAL_FIELDS:
        if getattr(app.partner, field): # Will be True if required by Partner.
            field_label = SEND_DATA_FIELD_LABELS[field]
            output[field] = {'label': field_label, 'data': getattr(app, field)}

    for field in USER_FORM_FIELDS:
        if getattr(app.partner, field): # Will be True if required by Partner.
            field_label = SEND_DATA_FIELD_LABELS[field]
            output[field] = {'label': field_label, 'data': getattr(app.editor, field)}

    return output


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
