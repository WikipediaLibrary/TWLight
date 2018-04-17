import django_filters
from taggit.managers import TaggableManager
from .models import Language,Partner

class PartnerFilter(django_filters.FilterSet):
    tags = django_filters.ModelChoiceFilter(queryset=Partner.tags.all())
    languages = django_filters.ModelChoiceFilter(queryset=Language.objects.all())
    class Meta:
        model = Partner
        fields = ['languages', 'tags']
