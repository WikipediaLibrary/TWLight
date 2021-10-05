from django import forms
from django.db.models import Q
from django.utils.translation import gettext as _

from .models import Language, Partner
from .helpers import get_tag_choices

import django_filters


class PartnerFilter(django_filters.FilterSet):

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

    searchable = django_filters.MultipleChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate if a collection is searchable.
        label=_("Searchable"),
        choices=Partner.SEARCHABLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, data=None, *args, **kwargs):
        # grab "language_code" from kwargs and then remove it so we can call super()
        language_code = None
        if "language_code" in kwargs:
            language_code = kwargs.get("language_code")
            kwargs.pop("language_code")

        # Set searchable to all selected by default
        # if filterset is bound, use initial values as defaults
        if data is not None:
            # get a mutable copy of the QueryDict
            data = data.copy()
            for name, f in self.base_filters.items():
                # filter param is either missing or empty, set all searchable values in MultiValueDict
                if name == "searchable" and not data.get(name):
                    data.setlist("searchable", ["0", "1", "2"])

        super(PartnerFilter, self).__init__(data, *args, **kwargs)
        self.filters["tags"].extra.update({"choices": get_tag_choices(language_code)})
        # Add CSS classes to style widgets
        self.filters["tags"].field.widget.attrs.update(
            {"class": "form-control form-control-sm"}
        )
        self.filters["languages"].field.widget.attrs.update(
            {"class": "form-control form-control-sm"}
        )
        self.filters["searchable"].field.widget.attrs.update(
            {"class": "searchable-form"}
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
