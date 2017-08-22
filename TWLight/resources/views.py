from django.contrib import messages
from django.contrib.auth.models import User
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic import ListView, DetailView, View

from TWLight.applications.models import Application
from TWLight.graphs.helpers import (get_median,
                                    get_application_status_data,
                                    get_data_count_by_month,
                                    get_users_by_partner_by_month)
from TWLight.view_mixins import CoordinatorsOnly

from .models import Partner



class PartnersListView(ListView):
    model = Partner

    def get_queryset(self):
        # The ordering here is useful primarily to people familiar with the
        # English alphabet. :/
        if self.request.user.is_staff:
            messages.add_message(self.request, messages.INFO,
                # Translators: Staff members can see partners on the Browse page (https://wikipedialibrary.wmflabs.org/partners/) which are hidden from other users.
                _('Because you are a staff member, this page may include '
                    'Partners who are not yet available to all users.'))
            return Partner.even_not_available.order_by('company_name')
        else:
            return Partner.objects.order_by('company_name')



class PartnersDetailView(DetailView):
    model = Partner

    def get_context_data(self, **kwargs):
        context = super(PartnersDetailView, self).get_context_data(**kwargs)

        partner = self.get_object()

        if partner.status == Partner.NOT_AVAILABLE:
            # This should be guaranteed by get_queryset and the manager
            # definitions.
            assert self.request.user.is_staff
            messages.add_message(self.request, messages.WARNING,
                _("This Partner is not available. You can see it because you "
                    "are a staff member, but it is not visible to non-staff 
                    "users."))

        context['total_apps'] = Application.objects.filter(
            partner=partner).count()

        context['total_apps_approved'] = Application.objects.filter(
            partner=partner, status=Application.APPROVED).count()

        context['total_apps_sent'] = Application.objects.filter(
            partner=partner, status=Application.SENT).count()

        context['total_apps_approved_or_sent'] = context['total_apps_approved'] + context['total_apps_sent']

        context['unique_users'] = User.objects.filter(
            editor__applications__partner=partner).distinct().count()

        context['unique_users_approved'] = User.objects.filter(
            editor__applications__partner=partner,
            editor__applications__status=Application.APPROVED).distinct().count()

        context['unique_users_sent'] = User.objects.filter(
            editor__applications__partner=partner,
            editor__applications__status=Application.SENT).distinct().count()

        context['unique_users_approved_or_sent'] = context['unique_users_approved'] + context['unique_users_sent']

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


    def get_queryset(self):
        if self.request.user.is_staff:
            return Partner.even_not_available.order_by('company_name')
        else:
            return Partner.objects.order_by('company_name')



class PartnersToggleWaitlistView(CoordinatorsOnly, View):
    def post(self, request, *args, **kwargs):
        try:
            # This only looks at AVAILABLE and WAITLIST partners, which is
            # good; we only want staff to be able to change the status of
            # NOT_AVAILABLE partners (using the admin interface).
            partner = Partner.objects.get(pk=self.kwargs['pk'])
        except Partner.DoesNotExist:
            raise Http404

        assert partner.status in [Partner.AVAILABLE, Partner.WAITLIST]

        if partner.status == Partner.AVAILABLE:
            partner.status = Partner.WAITLIST
            # Translators: When an account coordinator changes a partner from being open to applications to having a 'waitlist', they are shown this message.
            msg = _('This partner is now waitlisted')
        else:
            partner.status = Partner.AVAILABLE
            # Translators: When an account coordinator changes a partner from having a 'waitlist' to being open for applications, they are shown this message.
            msg = _('This partner is now available for applications')

        partner.save()

        messages.add_message(request, messages.SUCCESS, msg)
        return HttpResponseRedirect(partner.get_absolute_url())
