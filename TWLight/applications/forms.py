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


class BaseUserAppForm(forms.Form):
    """
    The BaseApplicationUserForm contains all possible user-data-related fields
    that an Application might need. applications/views will delete any fields
    that are unneeded for a given Application.

    For this reason, blank=True is not supplied; we don't want to have any
    optional fields, since the view present only the fields required for that
    application.

    Note: BooleanFields have required=False because otherwise Django will
    (foolishly) reject unchecked fields rather than interpreting them as
    False.
    """

    real_name = forms.BooleanField(required=False)
    country_of_residence = forms.BooleanField(required=False)
    specific_title = forms.BooleanField(required=False)
    specific_stream = forms.BooleanField(required=False)
    occupation = forms.BooleanField(required=False)
    affiliation = forms.BooleanField(required=False)



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
    partner = forms.ModelChoiceField(
        queryset=Partner.objects.all(),
        widget=forms.HiddenInput)
    rationale = forms.CharField(widget=forms.Textarea)
    title_requested = forms.CharField(max_length=128)
    stream_requested = forms.CharField(max_length=128)
    comments = forms.CharField(widget=forms.Textarea)
    agreement_with_terms = forms.BooleanField(required=False)
