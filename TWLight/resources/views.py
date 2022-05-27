from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.urls import reverse, reverse_lazy
from django.db.models import Count, Prefetch
from django.http import Http404, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, gettext as _
from django.views.generic import DetailView, View, RedirectView, ListView
from django.views.generic.edit import FormView, DeleteView
from django_filters.views import FilterView
from django.shortcuts import get_object_or_404

from TWLight.applications.helpers import count_valid_authorizations
from TWLight.applications.models import Application
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Authorization, User
from TWLight.view_mixins import (
    CoordinatorsOnly,
    PartnerCoordinatorOrSelf,
    EditorsOnly,
    StaffOnly,
)
from TWLight.users.helpers.editor_data import editor_bundle_eligible

from .filters import MainPartnerFilter, MergeSuggestionFilter
from .forms import SuggestionForm, SuggestionMergeForm
from .helpers import get_partner_description, get_tag_names, get_median
from .models import Partner, Suggestion
from urllib.parse import urlparse
import bleach
import logging

logger = logging.getLogger(__name__)


class PartnersFilterView(ListView):
    """
    Since T278337, this View has passed from FilterView to ListView because we have to
    build a Partner dictionary element from the partner descriptions in a JSON file instead of
    getting everything from the database
    """

    model = Partner

    def get_queryset(self):
        qs = (
            Partner.objects.prefetch_related("languages")
            .select_related("coordinator", "logos")
            .order_by("company_name")
        )
        # The ordering here is useful primarily to people familiar with the
        # English alphabet. :/
        if self.request.user.is_staff:
            messages.add_message(
                self.request,
                messages.INFO,
                "Because you are a staff member, this page may include "
                "Partners who are not yet available to all users.",
            )
            qs = (
                Partner.even_not_available.prefetch_related("languages")
                .select_related("coordinator", "logos")
                .order_by("company_name")
            )

        return qs

    def get_context_data(self, **kwargs):
        """
        We try to find out if the user has decided to filter by tags.
        If there's no filtering or tags involved, we carry on. Otherwise,
        we add the tag to the context and get the corresponding meta url
        in the template.
        :param kwargs:
        :return:
        """
        context = super().get_context_data(**kwargs)

        language_code = get_language()
        # Changed since T278337: add filter to queryset before we build the partners
        # dictionary
        partner_filtered_list = MainPartnerFilter(
            self.request.GET, queryset=self.get_queryset(), language_code=language_code
        )
        context["filter"] = partner_filtered_list

        user = self.request.user
        if user.is_authenticated:
            user = User.objects.select_related("editor").get(pk=self.request.user.pk)
            context["user"] = user
            context["editor"] = user.editor
        partners_list = []
        partner_search_list = []
        for partner in partner_filtered_list.qs:
            partner_dict = {}
            partner_dict["pk"] = partner.pk
            partner_dict["company_name"] = partner.company_name
            try:
                partner_dict["partner_logo"] = partner.logos.logo.url
            except ObjectDoesNotExist:
                partner_dict["partner_logo"] = None
            partner_dict["is_not_available"] = partner.is_not_available
            partner_dict["is_waitlisted"] = partner.is_waitlisted
            new_tags = partner.new_tags
            # Getting tags from locale files
            translated_tags = get_tag_names(language_code, new_tags)
            partner_dict["tags"] = translated_tags
            partner_dict["languages"] = partner.get_languages
            # Obtaining translated partner description
            partner_short_description_key = "{pk}_short_description".format(
                pk=partner.pk
            )
            partner_description_key = "{pk}_description".format(pk=partner.pk)
            partner_descriptions = get_partner_description(
                language_code, partner_short_description_key, partner_description_key
            )

            partner_dict["short_description"] = partner_descriptions[
                "short_description"
            ]
            partner_dict["description"] = partner_descriptions["description"]
            partners_list.append(partner_dict)
            if partner_descriptions["description"]:
                partner_desc = bleach.clean(
                    partner_descriptions["description"],
                    tags=[],
                    strip=True,
                )
            else:
                partner_desc = ""

            if partner_descriptions["short_description"]:
                partner_short_desc = bleach.clean(
                    partner_descriptions["short_description"],
                    tags=[],
                    strip=True,
                )
            else:
                partner_short_desc = ""

            partner_search_list.append(
                {
                    "partner_pk": partner.pk,
                    "partner_name": partner.company_name,
                    "partner_short_description": partner_short_desc,
                    "partner_description": partner_desc,
                }
            )
        context["partners_list"] = partners_list
        context["partner_search_list"] = partner_search_list

        return context


class PartnersDetailView(DetailView):
    model = Partner

    def get_context_data(self, **kwargs):
        context = super(PartnersDetailView, self).get_context_data(**kwargs)
        partner = self.get_object()

        # Obtaining translated partner description
        language_code = get_language()
        partner_short_description_key = "{pk}_short_description".format(pk=partner.pk)
        partner_description_key = "{pk}_description".format(pk=partner.pk)
        partner_descriptions = get_partner_description(
            language_code, partner_short_description_key, partner_description_key
        )

        context["partner_short_description"] = partner_descriptions["short_description"]
        context["partner_description"] = partner_descriptions["description"]

        context["tags"] = get_tag_names(language_code, partner.new_tags)

        if partner.status == Partner.NOT_AVAILABLE:
            messages.add_message(
                self.request,
                messages.WARNING,
                "This partner is not available. You can see it because you "
                "are a staff member, but it is not visible to non-staff "
                "users.",
            )

        context["total_accounts_distributed_partner"] = count_valid_authorizations(
            partner
        )

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
            self.request.user.is_authenticated
            and not partner.authorization_method == partner.BUNDLE
            and editor_bundle_eligible(self.request.user.editor)
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
            if apps.count() > 0:
                # User has open applications, don't show 'apply',
                # but link to apps page
                context["has_open_apps"] = True
                if not partner.specific_title:
                    self._evaluate_apply(context, partner)
            try:
                Authorization.objects.get(partners=partner, user=user)
                # User has an authorization, don't show 'apply',
                # but link to collection page
                if not partner.specific_title:
                    self._evaluate_apply(context, partner)
                self._evaluate_has_auths(context, user, partner)
            except Authorization.DoesNotExist:
                pass
            except Authorization.MultipleObjectsReturned:
                logger.info(
                    "Multiple authorizations returned for partner {} and user {}".format(
                        partner, user
                    )
                )
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    # fmt: off
                    # Translators: If multiple authorizations where returned for a partner with no collections, this message is shown to an user
                    _("Multiple authorizations were returned – something's wrong. Please contact us and don't forget to mention this message."),
                    # fmt: on
                )

        return context

    def get_queryset(self):
        # We have three types of users who might try to access partner pages - the partner's coordinator, staff,
        # and normal users. We want to limit the list of viewable partner pages in different ways for each.

        # By default users can only view available partners
        available_partners = Partner.objects.select_related(
            "coordinator", "logos"
        ).all()
        partner_list = available_partners

        # If logged in, what's the list of unavailable partners, if any, for which the current user is the coordinator?
        if self.request.user.is_authenticated:
            coordinator_partners = Partner.even_not_available.select_related(
                "coordinator", "logos"
            ).filter(coordinator=self.request.user, status=Partner.NOT_AVAILABLE)
            if coordinator_partners.exists():
                # Coordinated partners are also valid for this user to view
                partner_list = available_partners | coordinator_partners

        if self.request.user.is_staff:
            # Staff can see any partner pages, even unavailable ones.
            partner_list = Partner.even_not_available.select_related(
                "coordinator", "logos"
            ).all()

        return partner_list

    def get(self, request, *args, **kwargs):
        try:
            partner = self.get_object()
        except Http404:
            # If partner object does not exists check if the partner's status is NOT_AVAILABLE.
            partner_pk = self.kwargs.get("pk")
            if Partner.even_not_available.filter(pk=partner_pk).exists():
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    # Translators: This message is shown when user tries to access a NOT_AVAILABLE Partner
                    _("This partner is currently not open for applications"),
                )
                raise PermissionDenied

        # In all other cases call the default get method.
        return super(PartnersDetailView, self).get(request, *args, **kwargs)

    def _evaluate_has_auths(self, context, user, partner):
        """
        Evaluating if the Apply button will be enabled or disabled
        based on whether the user has agreed to the terms of service and if the
        partner authorization method is EMAIL, CODES, or LINK type

        Parameters
        ----------
        context: dict
            The context dictionary
        user : User
            The logged in user that navigated to the partner detail page
        partner: Partner
            The partner object to check what authorization methods it has

        Returns
        -------
        dict
            The context dictionary with a boolean value that notes whether a
            user has the required authorizations or not
        """
        # User fulfills initial authorization
        fulfills_auth = True
        # Checking if user has agreed to terms and conditions, otherwise
        # they shouldn't be authorized to access the collection
        user_agreed_terms = user.userprofile.terms_of_use

        if partner.authorization_method in [Partner.EMAIL, Partner.CODES, Partner.LINK]:
            partner_renew = True
            final_auth = fulfills_auth and user_agreed_terms and partner_renew
        else:
            final_auth = fulfills_auth and user_agreed_terms
        # User has authorizations, link to collection page
        context["has_auths"] = final_auth

        return context

    def _evaluate_apply(self, context, partner):
        """
        Evaluating if the Apply button will be enabled or disabled
        based on whether the user has agreed to the terms of service and if the
        partner authorization method is EMAIL, CODES, or LINK type

        Parameters
        ----------
        context: dict
            The context dictionary
        partner: Partner
            The partner object to check what authorization methods it has

        Returns
        -------
        dict
            The context dictionary with a boolean value that notes whether a
            user has the required authorizations or not
        """
        if partner.authorization_method in [
            Partner.EMAIL,
            Partner.CODES,
            Partner.LINK,
        ]:
            context["apply"] = True
        else:
            context["apply"] = False

        return context


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

            # Set waitlist_status to True for all the applications
            # which are Pending or Under Discussion for this partner
            applications = Application.objects.filter(
                partner=partner, status__in=[Application.PENDING, Application.QUESTION]
            )
            for app in applications:
                app.waitlist_status = True
                app.save()
        else:
            partner.status = Partner.AVAILABLE
            # Translators: When an account coordinator changes a partner from having a 'waitlist' to being open for applications, they are shown this message.
            msg = _("This partner is now available for applications")

        partner.save()

        messages.add_message(request, messages.SUCCESS, msg)
        return HttpResponseRedirect(partner.get_absolute_url())


class PartnerUsers(PartnerCoordinatorOrSelf, DetailView):
    model = Partner
    template_name_suffix = "_users"

    def get_context_data(self, **kwargs):
        context = super(PartnerUsers, self).get_context_data(**kwargs)

        partner = self.get_object()

        partner_applications = Application.objects.filter(partner=partner)

        context["approved_applications"] = partner_applications.filter(
            status=Application.APPROVED
        ).order_by("-date_closed")

        context["sent_applications"] = partner_applications.filter(
            status=Application.SENT
        ).order_by("-date_closed")

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

        user_qs = User.objects.select_related("editor")
        all_suggestions = (
            Suggestion.objects.all()
            .prefetch_related(Prefetch("author", queryset=user_qs))
            .prefetch_related("upvoted_users")
            .annotate(total_upvoted_users=Count("upvoted_users"))
            .order_by("-total_upvoted_users")
        )
        if all_suggestions.count() > 0:
            context["all_suggestions"] = all_suggestions

        else:
            context["all_suggestions"] = None

        # NOTE: Checking if a user is a coordinator or a superuser from the view.
        # Not using the coordinators_only template filter because of performance
        # issues
        user = self.request.user
        coordinators = get_coordinators()

        if coordinators in user.groups.all() or user.is_superuser:
            context["user_is_coordinator"] = True
        else:
            context["user_is_coordinator"] = False

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
        if user.is_authenticated:
            if user in obj.upvoted_users.all():
                obj.upvoted_users.remove(user)
            else:
                obj.upvoted_users.add(user)
        return url_


@method_decorator(login_required, name="post")
class SuggestionMergeView(StaffOnly, FormView):

    model = Suggestion
    template_name = "resources/merge_suggestion.html"
    form_class = SuggestionMergeForm
    success_url = reverse_lazy("suggest")

    def get_total_upvotes(self, suggestions, main_suggestion):
        """
        This function merges upvoted users for merged suggestions.

        Parameters
        ----------
        self : view object

        suggestions : Queryset<Suggestion>
            The queryset of suggestions to merge

        Returns
        -------
        The `queryset` of upvoted users

        """
        total_upvoted_users = main_suggestion.upvoted_users.all()
        for suggestion in suggestions.all():
            total_upvoted_users |= suggestion.upvoted_users.all()

        return total_upvoted_users.distinct()

    def get_queryset(self):
        user_qs = User.objects.select_related("editor")

        return (
            Suggestion.objects.all()
            .prefetch_related(Prefetch("author", queryset=user_qs))
            .prefetch_related("upvoted_users")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filter_suggestion = MergeSuggestionFilter(
            self.request.GET, queryset=self.get_queryset()
        )
        context["filter"] = filter_suggestion
        all_suggestions = filter_suggestion.qs

        if all_suggestions.count() > 0:
            context["all_suggestions"] = all_suggestions

        else:
            context["all_suggestions"] = None

        return context

    def form_valid(self, form):

        try:
            main_suggestion = form.cleaned_data["main_suggestion"]
            secondary_suggestions = Suggestion.objects.filter(
                id__in=form.cleaned_data["secondary_suggestions"].values_list(
                    "id", flat=True
                )
            ).exclude(id=main_suggestion.id)
            main_suggestion.upvoted_users.add(
                *self.get_total_upvotes(
                    suggestions=secondary_suggestions,
                    main_suggestion=main_suggestion,
                )
            )
            main_suggestion.save()

            # Old suggestions shall be spliced
            secondary_suggestions.delete()
            messages.add_message(
                self.request,
                messages.SUCCESS,
                "Suggestions merged successfully!",
            )
            return HttpResponseRedirect(self.success_url)

        except (AssertionError, AttributeError) as e:
            messages.add_message(
                self.request,
                messages.WARNING,
                "Some Error Occured",
            )
            raise PermissionDenied
