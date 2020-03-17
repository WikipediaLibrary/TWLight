from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, View, RedirectView
from django.views.generic.edit import FormView, DeleteView
from django_filters.views import FilterView
from django.shortcuts import get_object_or_404

from TWLight.applications.helpers import count_valid_authorizations
from TWLight.applications.models import Application
from TWLight.graphs.helpers import get_median
from TWLight.users.models import Authorization
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
            messages.add_message(
                self.request,
                messages.INFO,
                # Translators: Staff members can see partners on the Browse page (https://wikipedialibrary.wmflabs.org/partners/) which are hidden from other users.
                _(
                    "Because you are a staff member, this page may include "
                    "Partners who are not yet available to all users."
                ),
            )
            return Partner.even_not_available.order_by("company_name")
        else:
            return Partner.objects.order_by("company_name")


class PartnersDetailView(DetailView):
    model = Partner

    def get_context_data(self, **kwargs):
        context = super(PartnersDetailView, self).get_context_data(**kwargs)
        partner = self.get_object()
        if partner.status == Partner.NOT_AVAILABLE:
            # Translators: Staff members can view partner pages which are hidden from other users. This message appears on those specific partner resource pages.
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "This partner is not available. You can see it because you "
                    "are a staff member, but it is not visible to non-staff "
                    "users."
                ),
            )

        context["total_accounts_distributed_partner"] = count_valid_authorizations(
            partner
        )

        partner_streams = Stream.objects.filter(partner=partner)
        if partner_streams.count() > 0:
            context["total_accounts_distributed_streams"] = {}

            for stream in partner_streams:
                context["total_accounts_distributed_streams"][
                    stream
                ] = count_valid_authorizations(partner, stream)
        else:
            context["total_accounts_distributed_streams"] = None

        context["total_users"] = Authorization.objects.filter(partners=partner).count()

        application_end_states = [
            Application.APPROVED,
            Application.NOT_APPROVED,
            Application.SENT,
        ]
        partner_app_time = (
            Application.objects.filter(
                partner=partner, status__in=application_end_states
            )
            .exclude(imported=True)
            .values_list("days_open", flat=True)
        )

        if len(partner_app_time) > 0:
            context["median_days"] = get_median(list(partner_app_time))
        else:
            context["median_days"] = None

        # Find out if current user has authorizations/apps
        # and change the Apply button and the help text
        # behaviour accordingly
        context["apply"] = False
        context["has_open_apps"] = False
        context["has_auths"] = False
        if (
            self.request.user.is_authenticated()
            and not partner.authorization_method == partner.BUNDLE
        ):
            context["apply"] = True
            user = self.request.user
            apps = Application.objects.filter(
                status__in=[
                    Application.PENDING,
                    Application.QUESTION,
                    Application.APPROVED,
                ],
                partner=partner,
                editor=user.editor,
            )
            if partner_streams.count() == 0:
                if apps.count() > 0:
                    # User has open applications, don't show 'apply',
                    # but link to apps page
                    context["has_open_apps"] = True
                    if not partner.specific_title:
                        context["apply"] = False
                try:
                    Authorization.objects.get(partners=partner, user=user)
                    # User has an authorization, don't show 'apply',
                    # but link to collection page
                    if not partner.specific_title:
                        context["apply"] = False
                    context["has_auths"] = True
                except Authorization.DoesNotExist:
                    pass
                except Authorization.MultipleObjectsReturned:
                    logger.info(
                        "Multiple authorizations returned for partner {} and user {}"
                    ).format(partner, user)
                    # Translators: If multiple authorizations where returned for a partner with no collections, this message is shown to an user
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        _(
                            "Multiple authorizations were returned – something's wrong. "
                            "Please contact us and don't forget to mention this message."
                        ),
                    )
            else:
                authorizations = Authorization.objects.filter(
                    partner=partner, user=user
                )
                if authorizations.count() == partner_streams.count():
                    # User has correct number of auths, don't show 'apply',
                    # but link to collection page
                    context["apply"] = False
                    context["has_auths"] = True
                    if apps.count() > 0:
                        # User has open apps, link to apps page
                        context["has_open_apps"] = True
                else:
                    auth_streams = []
                    for each_authorization in authorizations:
                        # We are interested in the streams of existing authorizations
                        if each_authorization.stream in partner_streams:
                            auth_streams.append(each_authorization.stream)
                    if auth_streams:
                        # User has authorizations, link to collection page
                        context["has_auths"] = True
                    no_auth_streams = partner_streams.exclude(
                        name__in=auth_streams
                    )  # streams with no corresponding authorizations – we'll want to know if these have apps
                    if apps.count() > 0:
                        # User has open apps, link to apps page
                        context["has_open_apps"] = True
                        # The idea behind the logic below is to find out if we have
                        # at least a single stream the user hasn't applied to. If so,
                        # we show the apply button; if not, we disable it.
                        all_streams_have_apps = True
                        for each_no_auth_stream in no_auth_streams:
                            stream_has_app = False
                            for each_app in apps:
                                if each_app.specific_stream == each_no_auth_stream:
                                    stream_has_app = True
                                    break
                            if not stream_has_app:
                                all_streams_have_apps = False
                                break
                        if all_streams_have_apps:
                            context["apply"] = False
        return context

    def get_queryset(self):
        # We have three types of users who might try to access partner pages - the partner's coordinator, staff,
        # and normal users. We want to limit the list of viewable partner pages in different ways for each.

        # By default users can only view available partners
        available_partners = Partner.objects.all()
        partner_list = available_partners

        # If logged in, what's the list of unavailable partners, if any, for which the current user is the coordinator?
        if self.request.user.is_authenticated():
            coordinator_partners = Partner.even_not_available.filter(
                coordinator=self.request.user, status=Partner.NOT_AVAILABLE
            )
            if coordinator_partners.exists():
                # Coordinated partners are also valid for this user to view
                partner_list = available_partners | coordinator_partners

        if self.request.user.is_staff:
            # Staff can see any partner pages, even unavailable ones.
            partner_list = Partner.even_not_available.all()

        return partner_list


class PartnersToggleWaitlistView(CoordinatorsOnly, View):
    def post(self, request, *args, **kwargs):
        try:
            # This only looks at AVAILABLE and WAITLIST partners, which is
            # good; we only want staff to be able to change the status of
            # NOT_AVAILABLE partners (using the admin interface).
            partner = Partner.objects.get(pk=self.kwargs["pk"])
        except Partner.DoesNotExist:
            raise Http404

        assert partner.status in [Partner.AVAILABLE, Partner.WAITLIST]

        if partner.status == Partner.AVAILABLE:
            partner.status = Partner.WAITLIST
            # Translators: When an account coordinator changes a partner from being open to applications to having a 'waitlist', they are shown this message.
            msg = _("This partner is now waitlisted")
        else:
            partner.status = Partner.AVAILABLE
            # Translators: When an account coordinator changes a partner from having a 'waitlist' to being open for applications, they are shown this message.
            msg = _("This partner is now available for applications")

        partner.save()

        messages.add_message(request, messages.SUCCESS, msg)
        return HttpResponseRedirect(partner.get_absolute_url())


class PartnerUsers(CoordinatorOrSelf, DetailView):
    model = Partner
    template_name_suffix = "_users"

    def get_context_data(self, **kwargs):
        context = super(PartnerUsers, self).get_context_data(**kwargs)

        partner = self.get_object()

        partner_applications = Application.objects.filter(partner=partner)

        context["approved_applications"] = partner_applications.filter(
            status=Application.APPROVED
        ).order_by("-date_closed", "specific_stream")

        context["sent_applications"] = partner_applications.filter(
            status=Application.SENT
        ).order_by("-date_closed", "specific_stream")

        if Stream.objects.filter(partner=partner).count() > 0:
            context["partner_streams"] = True
        else:
            context["partner_streams"] = False

        return context


@method_decorator(login_required, name="post")
class PartnerSuggestionView(FormView):
    model = Suggestion
    template_name = "resources/suggest.html"
    form_class = SuggestionForm
    success_url = reverse_lazy("suggest")

    def get_initial(self):
        initial = super(PartnerSuggestionView, self).get_initial()
        # @TODO: This sort of gets repeated in SuggestionForm.
        # We could probably be factored out to a common place for DRYness.
        if "suggested_company_name" in self.request.GET:
            initial.update(
                {"suggested_company_name": self.request.GET["suggested_company_name"]}
            )
        if "description" in self.request.GET:
            initial.update({"description": self.request.GET["description"]})
        if "company_url" in self.request.GET:
            initial.update({"company_url": self.request.GET["company_url"]})

        initial.update({"next": reverse_lazy("suggest")})

        return initial

    def get_queryset(self):
        return Suggestion.objects.order_by("suggested_company_name")

    def get_context_data(self, **kwargs):

        context = super(PartnerSuggestionView, self).get_context_data(**kwargs)

        all_suggestions = (
            Suggestion.objects.all()
            .annotate(total_upvoted_users=Count("upvoted_users"))
            .order_by("-total_upvoted_users")
        )
        if all_suggestions.count() > 0:
            context["all_suggestions"] = all_suggestions

        else:
            context["all_suggestions"] = None

        return context

    def form_valid(self, form):
        # Adding an extra check to ensure the user is a wikipedia editor.
        try:
            assert self.request.user.editor
            suggestion = Suggestion()
            suggestion.suggested_company_name = form.cleaned_data[
                "suggested_company_name"
            ]
            suggestion.description = form.cleaned_data["description"]
            suggestion.company_url = form.cleaned_data["company_url"]
            suggestion.author = self.request.user
            suggestion.save()
            suggestion.upvoted_users.add(self.request.user)
            messages.add_message(
                self.request,
                messages.SUCCESS,
                # Translators: Shown to users when they successfully add a new partner suggestion.
                _("Your suggestion has been added."),
            )
            return HttpResponseRedirect(reverse("suggest"))
        except (AssertionError, AttributeError) as e:
            messages.add_message(
                self.request,
                messages.WARNING,
                # Translators: This message is shown to non-wikipedia editors who attempt to post data to suggestion form.
                _("You must be a Wikipedia editor to do that."),
            )
            raise PermissionDenied


class SuggestionDeleteView(CoordinatorsOnly, DeleteView):
    model = Suggestion
    form_class = SuggestionForm
    success_url = reverse_lazy("suggest")

    def delete(self, *args, **kwargs):
        suggestion = self.get_object()
        suggestion.delete()
        messages.add_message(
            self.request,
            messages.SUCCESS,
            # Translators: Shown to coordinators when they successfully delete a partner suggestion
            _("Suggestion has been deleted."),
        )
        return HttpResponseRedirect(self.success_url)


class SuggestionUpvoteView(EditorsOnly, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        suggestion_id = self.kwargs.get("pk")
        obj = get_object_or_404(Suggestion, id=suggestion_id)
        url_ = obj.get_absolute_url()
        user = self.request.user
        if user.is_authenticated():
            if user in obj.upvoted_users.all():
                obj.upvoted_users.remove(user)
            else:
                obj.upvoted_users.add(user)
        return url_
