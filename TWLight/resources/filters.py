import django_filters
from django.db import connection

from taggit.managers import TaggableManager
from .models import Language,Partner

class PartnerFilter(django_filters.FilterSet)
    # The combination of taggit and filters caused a bootstrapping problem.
    # This code depends on the django_content_type table which doesn't exist at
    # migration time for new builds, so it's wrapped in a check for the table.
    if 'django_content_type' in connection.introspection.table_names():
        tags = django_filters.ModelChoiceFilter(queryset=Partner.tags.all())
        languages = django_filters.ModelChoiceFilter(queryset=Language.objects.all())
        class Meta:
            model = Partner
            fields = ['languages', 'tags']
