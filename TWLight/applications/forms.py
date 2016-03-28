"""
This forms.py contains base forms that applications/views.py will use to
generate the actual forms filled in by users in making requests for partner
content.

For usability reasons, we only want users to have to fill in one form at a time
(even if they are requesting access to multiple partners' resources), and we
only want to ask them once for any piece of data even if multiple partners
require it, and we *don't* want to ask them for data that *isn't* required by
any of the partners in their set.

This means that the actual form we present to users must be generated
dynamically; we cannot hardcode it here. What we have here instead is a base
form that takes a dict of required fields, and constructs the form accordingly.
(See the docstring of BaseApplicationForm for the expected dict format.)
"""

import logging
import re

from django import forms

from TWLight.resources.models import Partner


logger = logging.getLogger(__name__)


# ~~~~~~ move these to helpers.py once you've got your head around them ~~~~~~ #

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


# ~~~~ Basic field names ~~~~ #
USER_FORM_FIELDS = ['real_name', 'country_of_residence', 'occupation',
                    'affiliation']

# These fields are displayed for all partners.
PARTNER_FORM_BASE_FIELDS = ['rationale', 'comments']

# These fields are displayed only when a specific partner requires that
# information.
PARTNER_FORM_OPTIONAL_FIELDS = ['specific_stream', 'specific_title',
                    'agreement_with_terms_of_use']


# ~~~~~~ Field types ~~~~~~ #
FIELD_TYPES = {
    REAL_NAME: forms.CharField(max_length=128),
    COUNTRY_OF_RESIDENCE: forms.CharField(max_length=128),
    OCCUPATION: forms.CharField(max_length=128),
    AFFILIATION: forms.CharField(max_length=128),
    PARTNER: forms.ModelChoiceField(
        queryset=Partner.objects.all(),
        widget=forms.HiddenInput),
    RATIONALE: forms.CharField(widget=forms.Textarea),
    SPECIFIC_STREAM: forms.CharField(max_length=128),
    SPECIFIC_TITLE: forms.CharField(max_length=128),
    COMMENTS: forms.CharField(widget=forms.Textarea, required=False),
    AGREEMENT_WITH_TERMS_OF_USE: forms.BooleanField(required=False),
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

class BaseApplicationForm(forms.Form):
    """
    Given a dict of parameters describing the required fields for this
    application, constructs a suitable application form.

    Expected dict format:
        {
            'user': [list, of, required, user, data, fields],
            'partner_1': [list, of, required, fields, for, partner, 1],
            'partner_2': [list, of, required, fields, for, partner, 2],
            (additional partners as needed)
        }

    'user' is mandatory. 'partner_1' is mandatory. Additional partners are
    optional.
    """
    def __init__(self, *args, **kwargs):
        self._validate_parameters(**kwargs)
        field_params = kwargs.pop('field_params')

        super(BaseApplicationForm, self).__init__(*args, **kwargs)

        user_data = field_params.pop('user')
        self._validate_user_data(user_data)

        for datum in user_data:
            self.fields[datum] = FIELD_TYPES[datum]

        for partner in field_params:
            partner_data = field_params[partner]
            self._validate_partner_data(partner, partner_data)

            for datum in partner_data:
                # This will yield fields with names like 'partner_1_occupation'.
                # This will let us tell during form processing which fields
                # belong to which partners.
                self.fields['{partner}_{datum}'.format(
                    partner=partner, datum=datum)] = FIELD_TYPES[datum]


    def _validate_parameters(self, **kwargs):
        """
        Ensure that parameters have been passed in and match the format
        specified in the docstring.
        """
        try:
            field_params = kwargs['field_params']
        except KeyError:
            logger.exception('Tried to instantiate a BaseApplicationForm but '
                'did not have field_params')
            raise

        try:
            assert 'user' in field_params
        except AssertionError:
            logger.exception('Tried to instantiate a BaseApplicationForm but '
                'there was no user parameter in field_params')
            raise

        try:
            # We should have 'user' plus at least one partner in the keys.
            assert len(field_params.keys()) >= 2
        except AssertionError:
            logger.exception('Tried to instantiate a BaseApplicationForm but '
                'there was not enough information in field_params')
            raise

        expected = re.compile(r'partner_\d+')

        for key in field_params.keys():
            # All keys which are not the user data should be partner data.
            if key != 'user':
                try:
                    assert expected.match(key)
                except AssertionError:
                    logger.exception('Tried to instantiate a BaseApplicationForm but '
                        'there was a key that did not match any expected values')


    def _validate_user_data(self, user_data):
        try:
            assert (set(user_data) <= set(USER_FORM_FIELDS))
        except AssertionError:
            logger.exception('BaseApplicationForm received invalid user data')
            raise


    def _validate_partner_data(self, partner, partner_data):
        try:
            assert (set(partner_data) <= set(PARTNER_FORM_OPTIONAL_FIELDS))

            # Extract the number component of (e.g.) 'partner_1'.
            partner_id = partner[8:]

            # Verify that it is the ID number of a real partner.
            partner = Partner.objects.get(id=partner_id)
        except (AssertionError, Partner.DoesNotExist):
            logger.exception('BaseApplicationForm received invalid partner data')
            raise
