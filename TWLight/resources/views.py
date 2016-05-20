from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView

from TWLight.applications.models import Application
from TWLight.graphs.helpers import (get_median,
                                    get_application_status_data,
                                    get_data_count_by_month,
                                    get_users_by_partner_by_month)

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

    def get_context_data(self, **kwargs):
        context = super(PartnersDetailView, self).get_context_data(**kwargs)

        partner = self.get_object()

        context['total_apps'] = Application.objects.filter(
            partner=partner).count()

        context['total_apps_approved'] = Application.objects.filter(
            partner=partner, status=Application.APPROVED).count()

        context['unique_users'] = User.objects.filter(
            applications__partner=partner).distinct().count()

        context['unique_users_approved'] = User.objects.filter(
            applications__partner=partner,
            applications__status=Application.APPROVED).distinct().count()

        partner_app_time = Application.objects.filter(
            partner=partner).values_list('days_open', flat=True)

        context['median_days'] = get_median(list(partner_app_time))

        context['app_distribution_data'] = get_application_status_data(
                Application.objects.filter(partner=partner)
            )

        context['signups_time_data'] = get_data_count_by_month(
                Application.objects.filter(partner=partner)
            )

        context['approved_signups_time_data'] = get_data_count_by_month(
                Application.objects.filter(
                    partner=partner,
                    status=Application.APPROVED
                )
            )

        context['users_time_data'] = get_users_by_partner_by_month(partner)

        return context
