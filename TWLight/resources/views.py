from django.contrib import messages
from django.contrib.auth.models import User
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, View
from django_filters.views import FilterView

from TWLight.applications.models import Application
from TWLight.graphs.helpers import (get_median,
                                    get_application_status_data,
                                    get_data_count_by_month,
                                    get_users_by_partner_by_month)
from TWLight.view_mixins import CoordinatorsOnly, CoordinatorOrSelf

from .models import Partner, Stream


class PartnersFilterView(FilterView):
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
            # Translators: Staff members can view partner pages which are hidden from other users. This message appears on those specific partner resource pages.
            messages.add_message(self.request, messages.WARNING,
                _("This partner is not available. You can see it because you "
                    "are a staff member, but it is not visible to non-staff "
                    "users."))

        context['total_apps'] = Application.objects.filter(
            partner=partner).count()

        context['total_apps_approved'] = Application.objects.filter(
            partner=partner, status=Application.APPROVED).count()

        context['total_apps_sent'] = Application.objects.filter(
            partner=partner, status=Application.SENT).count()

        context['total_apps_approved_or_sent'] = context['total_apps_approved'] + context['total_apps_sent']
        
        # This if else block supports the template with the number of accounts available 
        partner_streams = Stream.objects.filter(partner=partner)
        if partner_streams.count() > 0:
            context['total_accounts_available_current'] = {}
            for stream in partner_streams:
                context['total_apps_approved_or_sent_stream'] = User.objects.filter(
                                      editor__applications__partner=partner,
                                      editor__applications__status__in=(Application.APPROVED, Application.SENT),
                                      editor__applications__specific_stream=stream).count()
                
                total_accounts_available = stream.accounts_available
                context['total_accounts_available'] = total_accounts_available
                
                context['total_accounts_available_current'][stream.name] = context['total_accounts_available'] - context['total_apps_approved_or_sent_stream']
        else:
            context['total_apps_approved_or_sent_stream'] = None

            context['negation_total_apps_approved_or_sent'] = - context['total_apps_approved_or_sent']

        context['unique_users'] = User.objects.filter(
            editor__applications__partner=partner).distinct().count()

        context['unique_users_approved'] = User.objects.filter(
            editor__applications__partner=partner,
            editor__applications__status=Application.APPROVED).distinct().count()

        context['unique_users_sent'] = User.objects.filter(
            editor__applications__partner=partner,
            editor__applications__status=Application.SENT).distinct().count()

        context['unique_users_approved_or_sent'] = User.objects.filter(
            editor__applications__partner=partner,
            editor__applications__status__in=(Application.APPROVED, Application.SENT)).distinct().count()

        application_end_states = [Application.APPROVED, Application.NOT_APPROVED, Application.SENT]
        partner_app_time = Application.objects.filter(
            partner=partner, status__in=application_end_states).exclude(imported=True).values_list('days_open', flat=True)

        if len(partner_app_time) > 0:
            context['median_days'] = get_median(list(partner_app_time))
        else:
            context['median_days'] = None

        context['app_distribution_data'] = get_application_status_data(
                Application.objects.filter(partner=partner)
            )

        context['signups_time_data'] = get_data_count_by_month(
                Application.objects.filter(partner=partner)
            )

        context['approved_or_sent_signups_time_data'] = get_data_count_by_month(
                Application.objects.filter(
                    partner=partner,
                    status__in=(Application.APPROVED, Application.SENT)
                )
            )

        context['users_time_data'] = get_users_by_partner_by_month(partner)

        # Find out if current user has applications and change the Apply
        # button behaviour accordingly
        if self.request.user.is_authenticated() and not partner.bundle:
            sent_apps = Application.objects.filter(
                                        editor=self.request.user.editor,
                                        status=Application.SENT,
                                        partner=partner
                                     ).order_by('date_closed')
            open_apps = Application.objects.filter(
                                        editor=self.request.user.editor,
                                        status__in=(Application.PENDING, Application.QUESTION, Application.APPROVED),
                                        partner=partner
                                     )
            context['user_sent_apps'] = False
            context['user_open_apps'] = False
            if sent_apps.count() > 0:
                context['latest_sent_app_pk'] = sent_apps[0].pk
                context['user_sent_apps'] = True
            elif open_apps.count() > 0:
                context['user_open_apps'] = True
                if open_apps.count() > 1:
                    context['multiple_open_apps'] = True
                else:
                    context['multiple_open_apps'] = False
                    context['open_app_pk'] = open_apps[0].pk

        partner_streams = Stream.objects.filter(partner=partner)
        if partner_streams.count() > 0:
            context['stream_unique_accepted'] = {}
            for stream in partner_streams:
                stream_unique_accepted = User.objects.filter(
                                      editor__applications__partner=partner,
                                      editor__applications__status__in=(Application.APPROVED, Application.SENT),
                                      editor__applications__specific_stream=stream).distinct().count()
                context['stream_unique_accepted'][stream.name] = stream_unique_accepted
        else:
            context['stream_unique_accepted'] = None

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



class PartnerUsers(CoordinatorOrSelf, DetailView):
    model = Partner
    template_name_suffix = '_users'

    def get_context_data(self, **kwargs):
        context = super(PartnerUsers, self).get_context_data(**kwargs)

        partner = self.get_object()

        partner_applications = Application.objects.filter(
            partner=partner)

        context['approved_applications'] = partner_applications.filter(
            status=Application.APPROVED).order_by(
                '-date_closed', 'specific_stream')

        context['sent_applications'] = partner_applications.filter(
            status=Application.SENT).order_by(
                '-date_closed', 'specific_stream')

        if Stream.objects.filter(partner=partner).count() > 0:
            context['partner_streams'] = True
        else:
            context['partner_streams'] = False

        return context
