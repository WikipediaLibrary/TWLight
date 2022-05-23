from django import forms
from django.db.models import Q, Value, F, CharField
from django.utils.translation import ugettext_lazy as _

from .models import Language, Partner, Suggestion
from .helpers import get_tag_choices

import django_filters

INSTANT = 0
MULTI_STEP = 1
ACCESS_CHOICES = (
    # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this indicates that a collection may be accessed immediately.
    (INSTANT, _("Instant (proxy) access")),
    # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this indicates that a collection may be accessed only after additional steps, such as submitting an application and awaiting approval.
    (MULTI_STEP, _("Multi-step access")),
)


class MainPartnerFilter(django_filters.FilterSet):
    """
    This filter is for the /partners page
    """

    tags = django_filters.ChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate how many subject areas a collection covers.
        label=_("Topics"),
        choices=get_tag_choices(),
        method="tags_filter",
    )

    languages = django_filters.ModelChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate how many languages a collection supports.
        label=_("Languages"),
        queryset=Language.objects.all(),
    )

    def __init__(self, data=None, *args, **kwargs):
        # grab "language_code" from kwargs and then remove it so we can call super()
        language_code = None
        if "language_code" in kwargs:
            language_code = kwargs.get("language_code")
            kwargs.pop("language_code")

        super().__init__(data, *args, **kwargs)
        self.filters["tags"].extra.update({"choices": get_tag_choices(language_code)})
        # Add CSS classes to style widgets
        self.filters["tags"].field.widget.attrs.update(
            {"class": "form-control form-control-sm"}
        )
        self.filters["languages"].field.widget.attrs.update(
            {"class": "form-control form-control-sm"}
        )

    class Meta:
        model = Partner
        fields = ["languages"]

    def tags_filter(self, queryset, name, value):
        tag_filter = queryset.filter(
            Q(new_tags__tags__contains=value)
            | Q(new_tags__tags__contains="multidisciplinary_tag")
        )
        return tag_filter


class PartnerFilter(MainPartnerFilter):
    """
    This filter is used in the MyLibrary page
    """

    searchable = django_filters.MultipleChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate if a collection is searchable.
        label=_("Searchable"),
        choices=Partner.SEARCHABLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    access = django_filters.MultipleChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate if a collection has instant or multi-step access.
        label=_("Access"),
        choices=ACCESS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        method="access_filter",
    )

    def __init__(self, data=None, *args, **kwargs):
        # Set searchable to all selected by default
        # if filterset is bound, use initial values as defaults
        if data is not None:
            # get a mutable copy of the QueryDict
            data = data.copy()
            for name, f in self.base_filters.items():
                # filter param is either missing or empty, set all searchable values in MultiValueDict
                if name == "searchable" and not data.get(name):
                    data.setlist("searchable", ["0", "1", "2"])
                if name == "access" and not data.get(name):
                    data.setlist("access", ["0", "1"])

        super().__init__(data, *args, **kwargs)
        self.filters["searchable"].field.widget.attrs.update(
            {"class": "checkbox-filter-form"}
        )
        self.filters["access"].field.widget.attrs.update(
            {"class": "checkbox-filter-form"}
        )

    def access_filter(self, queryset, name, value):
        queryset = queryset.prefetch_related("languages").select_related("logos")
        if str(INSTANT) in value and str(MULTI_STEP) in value:
            return queryset
        else:
            if str(INSTANT) in value:
                return queryset.filter(
                    authorization_method__in=[Partner.PROXY, Partner.BUNDLE]
                )
            elif str(MULTI_STEP) in value:
                return queryset.exclude(
                    authorization_method__in=[Partner.PROXY, Partner.BUNDLE]
                )

        return queryset


class MergeSuggestionFilter(django_filters.FilterSet):
    """Filter based on URL name"""

    company_url = django_filters.CharFilter(
        label="Search via URL",
        field_name="company_url",
        method="filter_company_url",
    )

    def filter_company_url(self, queryset, name, value):
        # Utility to filter suggestions based on common url
        lookup = "__".join([name, "icontains"])

        qs = queryset.filter(**{lookup: value})
        return qs.distinct()

    class Meta:
        model = Suggestion
        fields = ["company_url"]

    def __init__(self, data=None, *args, **kwargs) -> None:
        super().__init__(data, *args, **kwargs)
        self.filters["company_url"].field.widget.attrs.update(
            {"class": "form-control form-control-sm"}
        )
