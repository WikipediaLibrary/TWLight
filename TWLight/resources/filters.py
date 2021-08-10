from django.utils.translation import gettext as _

from .models import Language, Partner
from .helpers import get_tag_choices

import django_filters


class PartnerFilter(django_filters.FilterSet):

    tags = django_filters.ChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate how many subject areas a collection covers.
        label=_("Tags"),
        choices=get_tag_choices(),
        method="tags_filter",
    )

    languages = django_filters.ModelChoiceFilter(
        # Translators: On the MyLibrary page (https://wikipedialibrary.wmflabs.org/users/my_library), this text is shown to indicate how many languages a collection supports.
        label=_("Languages"),
        queryset=Language.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        # grab "language_code" from kwargs and then remove it so we can call super()
        language_code = None
        if "language_code" in kwargs:
            language_code = kwargs.get("language_code")
            kwargs.pop("language_code")
        super(PartnerFilter, self).__init__(*args, **kwargs)
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

        return queryset.filter(new_tags__tags__contains=value)
