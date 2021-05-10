import django_filters

from .models import Language, Partner
from .helpers import get_tag_choices


class PartnerFilter(django_filters.FilterSet):
    tags = django_filters.ChoiceFilter(
        label="Tags", choices=get_tag_choices(), method="tags_filter"
    )
    languages = django_filters.ModelChoiceFilter(queryset=Language.objects.all())

    def __init__(self, *args, **kwargs):
        # grab "language_code" from kwargs and then remove it so we can call super()
        language_code = None
        if "language_code" in kwargs:
            language_code = kwargs.get("language_code")
            kwargs.pop("language_code")
        super(PartnerFilter, self).__init__(*args, **kwargs)
        self.filters["tags"].extra.update({"choices": get_tag_choices(language_code)})

    class Meta:
        model = Partner
        fields = ["languages"]

    def tags_filter(self, queryset, name, value):

        return queryset.filter(new_tags__tags__contains=value)
