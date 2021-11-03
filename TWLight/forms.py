from crispy_forms.helper import FormHelper
from crispy_forms.layout import Hidden, Submit, Layout

from django.conf import settings
from django.contrib.auth.models import User

from django import forms
from django.utils.translation import gettext as _


class EdsSearchForm(forms.Form):
    """ """

    lang = forms.ChoiceField(choices=settings.LANGUAGES)
    schemaId = forms.CharField()
    custid = forms.CharField()
    groupid = forms.CharField()
    profid = forms.CharField()
    scope = forms.CharField()
    site = forms.CharField()
    direct = forms.CharField()
    authtype = forms.CharField()
    bquery = forms.CharField()

    def __init__(self, *args, **kwargs):
        bquery = kwargs.pop("bquery", None)
        super().__init__(*args, **kwargs)
        if bquery:
            self.fields["bquery"].initial = bquery
        self.fields["schemaId"].initial = "search"
        self.fields["custid"].initial = "ns253359"
        self.fields["groupid"].initial = "main"
        self.fields["profid"].initial = "eds"
        self.fields["scope"].initial = "site"
        self.fields["site"].initial = "eds-live"
        self.fields["direct"].initial = "true"
        self.fields["authtype"].initial = "url"
        self.helper = FormHelper()
        self.helper.form_action = "https://searchbox.ebsco.com/search/"
        self.helper.form_method = "GET"
        self.helper.label_class = "sr-only"
        self.helper.layout = Layout(
            "bquery",
            Hidden("lang", "en"),
            Hidden("schemaId", "search"),
            Hidden("custid", "ns253359"),
            Hidden("groupid", "main"),
            Hidden("profid", "eds"),
            Hidden("scope", "site"),
            Hidden("site", "eds-live"),
            Hidden("direct", "true"),
            Hidden("authtype", "url"),
            Submit(
                "submit",
                # Translators: This labels a button which users click to change their email.
                _("Search"),
                css_class="btn btn-default col-md-offset-2",
            ),
        )
