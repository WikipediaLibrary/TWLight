import django_filters

from .models import Language, Partner
from .helpers import get_tag_choices


class PartnerFilter(django_filters.FilterSet):
    tags = django_filters.ChoiceFilter(choices=get_tag_choices(), method="tags_filter")
    languages = django_filters.ModelChoiceFilter(queryset=Language.objects.all())

    class Meta:
        model = Partner
        fields = ["languages"]

    def tags_filter(self, queryset, name, value):

        return queryset.filter(new_tags__tags__contains=value)
