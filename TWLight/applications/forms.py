"""
This forms.py contains base forms that applications/views.py will use to
generate the actual forms filled in by users in making requests for partner
content.

For usability reasons, we only want users to have to fill in one form at a time
(even if they are requesting access to multiple partners' resources), and we
only want to ask them once for any piece of data even if multiple partners
require it, and we *don't* want to ask them for data that *isn't* required by
any of the partners in their set.

These base forms contain *all* the data that an application might conceivably
require. In views.py, we'll hide the ones not needed for any particular
access grant request, and require. This is easier and more readable than constructing them on
the fly.
"""

from django import forms

from TWLight.resources.models import Partner

USER_FORM_FIELDS = ['real_name', 'country_of_residence', 'occupation',
                    'affiliation']

PARTNER_FORM_FIELDS = ['specific_stream', 'specific_title',
                       'agreement_with_terms_of_use']


class BaseUserAppForm(forms.Form):
    """
    The BaseApplicationUserForm contains all possible user-data-related fields
    that an Application might need. You can delete any fields that are unneeded
    for a given Application by passing a fields_to_remove list into the
    constructor.

    For this reason, blank=True is not supplied; we don't want to have any
    optional fields, since the view is expected to present only the fields
    required for its Application.

    Note: BooleanFields have required=False because otherwise Django will
    (foolishly) reject unchecked fields rather than interpreting them as
    False.
    """

    def __init__(self, fields_to_remove=None, *args, **kwargs):
        """
        Sets up form, then removes any fields that are unneeded for this
        instance.
        """
        super(BaseUserAppForm, self).__init__(*args, **kwargs)
        for field in fields_to_remove:
            del self.fields[field]

    real_name = forms.CharField(max_length=128)
    country_of_residence = forms.CharField(max_length=128)
    occupation = forms.CharField(max_length=128)
    affiliation = forms.CharField(max_length=128)



class BasePartnerAppForm(forms.Form):
    """
    As BaseApplicationUserForm, but for data that adheres to individual partner
    requests.

    We separate the forms because we will only ever need one
    BaseApplicationUserForm per request (as there is only one user to harvest
    data from), but different partners may want different information.
    Furthermore, even where partners want the same fields, the data in those
    fields will differ (you cannot have one checkbox governing agreement with
    two different entities' terms of use; you cannot expect the title being
    requested from each partner to be the same; etc.)
    """
    def __init__(self, *args, **kwargs):
        """
        Sets up form; then, if a partner has been provided, removes any fields
        not required by that partner.
        """
        super(BasePartnerAppForm, self).__init__(*args, **kwargs)
        if 'partner' in self.initial.keys():
            partner = self.initial['partner']
            for field in PARTNER_FORM_FIELDS:
                if not getattr(partner, field):
                    del self.fields[field]


    partner = forms.ModelChoiceField(
        queryset=Partner.objects.all(),
        widget=forms.HiddenInput)
    rationale = forms.CharField(widget=forms.Textarea)
    specific_stream = forms.CharField(max_length=128)
    specific_title = forms.CharField(max_length=128)
    comments = forms.CharField(widget=forms.Textarea, required=False)
    agreement_with_terms_of_use = forms.BooleanField(required=False)
