import django_filters

from .models import Language,Partner

# The combination of taggit and filters caused a bootstrapping problem.
# This code can run before the taggit migrations have run, meaning the tables
# don't yet exist;, so it needs to be a function.
def get_partner_tags():
    try:
        return Partner.tags.all()
    except:
        pass

class PartnerFilter(django_filters.FilterSet):
    tags = django_filters.ModelChoiceFilter(queryset=get_partner_tags())
    languages = django_filters.ModelChoiceFilter(queryset=Language.objects.all())
    class Meta:
        model = Partner
        fields = ['languages', 'tags']
