from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, View, RedirectView
from django.views.generic.edit import FormView, DeleteView
from django_filters.views import FilterView
from django.shortcuts import get_object_or_404

from TWLight.applications.models import Application
from TWLight.graphs.helpers import (get_median,
                                    get_application_status_data,
                                    get_data_count_by_month,
                                    get_users_by_partner_by_month,
                                    get_earliest_creation_date)
from TWLight.view_mixins import CoordinatorsOnly, CoordinatorOrSelf, EditorsOnly

from .forms import SuggestionForm
from .models import Partner, Stream, Suggestion

import logging

logger = logging.getLogger(__name__)

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
        context['partner_streams'] = partner_streams
        
        if partner_streams.count() > 0:
            context['total_accounts_available_stream'] = {}
            context['stream_unique_accepted'] = {}
            
            for stream in partner_streams:
                if stream.accounts_available is not None:
                    total_apps_approved_or_sent_stream = User.objects.filter(
                                          editor__applications__partner=partner,
                                          editor__applications__status__in=(Application.APPROVED, Application.SENT),
                                          editor__applications__specific_stream=stream).count()
                    
                    total_accounts_available = stream.accounts_available
                    
                    context['total_accounts_available_stream'][stream.name] = total_accounts_available - total_apps_approved_or_sent_stream
                
                stream_unique_accepted = User.objects.filter(
                                      editor__applications__partner=partner,
                                      editor__applications__status__in=(Application.APPROVED, Application.SENT),
                                      editor__applications__specific_stream=stream).distinct().count()
                context['stream_unique_accepted'][stream.name] = stream_unique_accepted
                
        else:
            context['total_accounts_available_stream'] = None
            context['stream_unique_accepted'] = None
            
            if partner.accounts_available is not None:
                context['total_accounts_available_partner'] = partner.accounts_available - context['total_apps_approved_or_sent']

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

        # To restrict the graph from rendering, if there's only a week's worth of data
        earliest_date = get_earliest_creation_date(
                Application.objects.filter(partner=partner)
            )
        
        context['insufficient_data'] = False
        if earliest_date:
            current_date = timezone.now().date()
            days_since_earliest_application = (current_date - earliest_date).days

            if days_since_earliest_application < 7:
                # Less than a week's of data
                context['insufficient_data'] = True

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
                                     ).order_by('-date_closed')
            open_apps = Application.objects.filter(
                                        editor=self.request.user.editor,
                                        status__in=(Application.PENDING, Application.QUESTION, Application.APPROVED),
                                        partner=partner
                                     )
            context['user_sent_apps'] = False
            context['user_open_apps'] = False
            if open_apps.count() > 0:
                context['user_open_apps'] = True
                if open_apps.count() > 1:
                    context['multiple_open_apps'] = True
                else:
                    context['multiple_open_apps'] = False
                    context['open_app_pk'] = open_apps[0].pk
            elif sent_apps.count() > 0:
                context['latest_sent_app_pk'] = sent_apps[0].pk
                context['user_sent_apps'] = True

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


@method_decorator(login_required, name='post')
class PartnerSuggestionView(FormView):
    model=Suggestion
    template_name = 'resources/suggest.html'
    form_class = SuggestionForm
    success_url = reverse_lazy('suggest')

    def get_initial(self):
        initial = super(PartnerSuggestionView, self).get_initial()
        # @TODO: This sort of gets repeated in SuggestionForm.
        # We could probably be factored out to a common place for DRYness.
        if ('suggested_company_name' in self.request.GET):
            initial.update({
                 'suggested_company_name': self.request.GET['suggested_company_name'],
            })
        if ('description' in self.request.GET):
            initial.update({
                 'description': self.request.GET['description'],
            })
        if ('company_url' in self.request.GET):
            initial.update({
                 'company_url': self.request.GET['company_url'],
            })

        initial.update({
            'next': reverse_lazy('suggest'),
        })

        return initial

    def get_queryset(self):
            return Suggestion.objects.order_by('suggested_company_name')

    def get_context_data(self, **kwargs):

        context = super(PartnerSuggestionView, self).get_context_data(**kwargs)
        
        all_suggestions = Suggestion.objects.all()
        if all_suggestions.count() > 0:
            context['all_suggestions'] = all_suggestions
        
        else:
            context['all_suggestions'] = None
        
        return context

    def form_valid(self, form):
        # Adding an extra check to ensure the user is a wikipedia editor.
        try:
            assert self.request.user.editor
            suggestion = Suggestion()
            suggestion.suggested_company_name = form.cleaned_data['suggested_company_name']
            suggestion.description = form.cleaned_data['description']
            suggestion.company_url = form.cleaned_data['company_url']
            suggestion.author = self.request.user
            suggestion.save()
            suggestion.upvoted_users.add(self.request.user)
            messages.add_message(self.request, messages.SUCCESS,
            # Translators: Shown to users when they successfully add a new partner suggestion.
            _('Your suggestion has been added.'))
            return HttpResponseRedirect(reverse('suggest'))
        except (AssertionError, AttributeError) as e:
            messages.add_message (self.request, messages.WARNING,
                # Translators: This message is shown to non-wikipedia editors who attempt to post data to suggestion form.
                _('You must be a Wikipedia editor to do that.'))
            raise PermissionDenied
        return self.request.user.editor


class SuggestionDeleteView(CoordinatorsOnly, DeleteView):
    model=Suggestion
    form_class = SuggestionForm
    success_url = reverse_lazy('suggest')
            
    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.add_message(self.request, messages.SUCCESS,
        # Translators: Shown to coordinators when they successfully delete a partner suggestion
        _('Suggestion has been deleted.'))
        return HttpResponseRedirect(self.success_url)



class SuggestionUpvoteView(EditorsOnly, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        id = self.kwargs.get('pk')
        obj = get_object_or_404(Suggestion, id=id)
        url_ = obj.get_absolute_url()
        user = self.request.user
        if user.is_authenticated():
            if user in obj.upvoted_users.all():
                obj.upvoted_users.remove(user)
            else:
                obj.upvoted_users.add(user)
        return url_
