from crispy_forms.helper import FormHelper
from crispy_forms.layout import Hidden, Submit, Layout

from django.conf import settings
from django.contrib.auth.models import User

from django import forms
from django.utils.translation import get_language, gettext as _


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
        language_code = get_language()
        lang = language_code
        bquery = kwargs.pop("bquery", None)

        super().__init__(*args, **kwargs)
        if language_code == "pt":
            lang = "pt-pt"
        elif language_code == "zh-hans":
            lang = "zh-cn"
        elif language_code == "zh-hant":
            lang = "zh-tw"
        self.helper = FormHelper()
        self.helper.form_id = "search"
        self.helper.form_action = "https://searchbox.ebsco.com/search/"
        self.helper.form_method = "GET"
        self.helper.label_class = "sr-only"
        self.helper.layout = Layout(
            Hidden("bquery", bquery),
            Hidden("lang", lang),
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
                # Translators: Shown in the search button.
                _("Search"),
                css_class="btn eds-search-button",
            ),
        )
