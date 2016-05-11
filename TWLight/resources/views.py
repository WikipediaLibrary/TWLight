from django.views.generic import ListView, DetailView

from .models import Partner


class PartnersListView(ListView):
    model = Partner

    def get_queryset(self):
        # Useful primarily to people familiar with the English alphabet. :/
        # But coordinators are required to have English proficiency, so this
        # should cover most page visitors.
        return Partner.objects.order_by('company_name')



class PartnersDetailView(DetailView):
    model = Partner
