"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
import logging
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlparse
from datetime import datetime, timedelta

import bleach
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse, reverse_lazy
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView
from reversion import revisions as reversion
from reversion.models import Version

from TWLight.users.helpers.editor_data import editor_bundle_eligible
from TWLight.applications.signals import no_more_accounts
from TWLight.resources.models import Partner, AccessCode
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Authorization, Editor
from TWLight.view_mixins import (
    PartnerCoordinatorOrSelf,
    CoordinatorsOnly,
    PartnerCoordinatorOnly,
    EditorsOnly,
    ToURequired,
    EmailRequired,
    SelfOnly,
    DataProcessingRequired,
    NotDeleted,
)
from .forms import BaseApplicationForm, ApplicationAutocomplete, RenewalForm
from .helpers import (
    USER_FORM_FIELDS,
    PARTNER_FORM_OPTIONAL_FIELDS,
    PARTNER_FORM_BASE_FIELDS,
    get_output_for_application,
    count_valid_authorizations,
    get_accounts_available,
    is_proxy_and_application_approved,
    more_applications_than_accounts_available,
)
from .models import Application

logger = logging.getLogger(__name__)

coordinators = get_coordinators()

PARTNERS_SESSION_KEY = "applications_request__partner_ids"


class EditorAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Make sure that we aren't leaking info via our form choices.
        if self.request.user.is_superuser:
            editor_qs = Editor.objects.all().order_by("wp_username")
            # Query by wikimedia username
            if self.q:
                editor_qs = editor_qs.filter(wp_username__istartswith=self.q).order_by(
                    "wp_username"
                )
        elif coordinators in self.request.user.groups.all():
            editor_qs = Editor.objects.filter(
                applications__partner__coordinator__pk=self.request.user.pk
            ).order_by("wp_username")
            # Query by wikimedia username
            if self.q:
                editor_qs = editor_qs.filter(wp_username__istartswith=self.q).order_by(
                    "wp_username"
                )
        else:
            editor_qs = Editor.objects.none()
        return editor_qs


class PartnerAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Make sure that we aren't leaking info via our form choices.
        if self.request.user.is_superuser:
            partner_qs = Partner.objects.filter(
                ~Q(authorization_method=Partner.BUNDLE)
            ).order_by("company_name")
            # Query by partner name
            if self.q:
                partner_qs = partner_qs.filter(
                    company_name__istartswith=self.q
                ).order_by("company_name")
        elif coordinators in self.request.user.groups.all():
            partner_qs = Partner.objects.filter(
                coordinator__pk=self.request.user.pk
            ).order_by("company_name")
            # Query by partner name
            if self.q:
                partner_qs = partner_qs.filter(
                    company_name__istartswith=self.q
                ).order_by("company_name")
        else:
            partner_qs = Partner.objects.none()
        return partner_qs


class SubmitSingleApplicationView(
    EditorsOnly, ToURequired, EmailRequired, DataProcessingRequired, FormView
):

    template_name = "applications/apply.html"
    form_class = BaseApplicationForm

    # ~~~~~~~~~~~~~~~~~ Overrides to built-in Django functions ~~~~~~~~~~~~~~~~#

    def dispatch(self, request, *args, **kwargs):
        partner = self._get_partner()
        if partner.authorization_method == Partner.BUNDLE:
            raise PermissionDenied
        elif partner.status == Partner.WAITLIST:
            messages.add_message(
                request,
                messages.WARNING,
                # fmt: off
                # Translators: When a user applies for a set of resources, they receive this message if none are currently available. They are instead placed on a 'waitlist' for later approval.
                _("This partner does not have any access grants available at this time. You may still apply for access; your application will be reviewed when access grants become available."),
                # fmt: on
            )

        if self._check_duplicate_applications(partner):
            # if duplicate applications exists then
            # redirect user to specific page with error message
            url, message = self._check_duplicate_applications(partner)
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(url, message)

        # Non-eligible users should redirect to my library page
        if not editor_bundle_eligible(self.request.user.editor):
            return HttpResponseRedirect(reverse("users:my_library"))

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            # fmt: off
            # Translators: This message is shown to users once they've successfully submitted their application for review.
            _("Your application has been submitted for review. Head over to <a href='{applications_url}'>My Applications</a> to view the status.")
            .format(
                applications_url=reverse_lazy(
                    "users:my_applications",
                    kwargs={"pk": self.request.user.editor.pk},
                )
            ),
            # fmt: on
        )
        user_home = self._get_partner().get_absolute_url()
        return user_home

    def get_form(self, form_class=None):
        """
        We will dynamically construct a form which harvests exactly the
        information needed for editors to request access to their desired collection.
        (Most of the actual work of form construction happens
        in applications/forms.py. This view figures out what data to pass to
        the base form's constructor: which information the partner in this
        application requires.)

        In particular:
        * We don't ask for information that we can harvest from their user
          profile.
        * We will ask for optional information if and only if the
          requested partner requires it.

        The goal is to reduce the user's data entry burden to the minimum
        amount necessary for applications to be reviewed.
        """
        if form_class is None:
            form_class = self.form_class

        kwargs = self.get_form_kwargs()

        field_params = {}
        partner = self._get_partner()
        user_fields = self._get_user_fields(partner)

        field_params["user"] = user_fields

        partner_fields = self._get_partner_fields(partner)
        field_params["partner"] = partner_fields
        field_params["partner_id"] = partner.id

        kwargs["field_params"] = field_params

        return form_class(**kwargs)

    def get_initial(self):
        """
        If we already know the user's real name, etc., use that to prefill form
        fields.
        """
        initial = super().get_initial()
        editor = self.request.user.editor

        # Our form might not actually have all these fields, but that's OK;
        # unneeded initial data will be discarded.
        for field in USER_FORM_FIELDS:
            initial[field] = getattr(editor, field)

        return initial

    def form_valid(self, form):
        # Add user data to user profile.
        editor = self.request.user.editor
        for field in USER_FORM_FIELDS:
            if field in form.cleaned_data:
                setattr(editor, field, form.cleaned_data[field])

        editor.save()

        # Create an Application for the partner resource. Remember that the
        # partner parameters were added as an attribute on the form during
        # form __init__, so we have them available now; no need to re-process
        # them out of our session data. They were also validated during form
        # instantiation; we rely on that validation here.
        partner_fields = PARTNER_FORM_BASE_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS
        partner_id = form.field_params["partner_id"]
        partner_obj = self._get_partner()

        # We exclude Bundle partners from the apply page, but if they are
        # here somehow, we can be reasonably certain something has gone awry.
        if partner_obj.authorization_method == Partner.BUNDLE:
            raise PermissionDenied

        app = Application()
        app.editor = self.request.user.editor
        app.partner = partner_obj

        # Application created for a WAITLISTED Partners
        # should have waitlist_status as True
        if app.partner.status == Partner.WAITLIST:
            app.waitlist_status = True

        # Status will be set to PENDING by default.

        for field in partner_fields:
            label = "partner_{field}".format(field=field)

            try:
                data = form.cleaned_data[label]
            except KeyError:
                # Not all forms require all fields, and that's OK. However,
                # we do need to make sure to clear out the value of data
                # here, or we'll have carried it over from the previous
                # time through the loop, and who knows what sort of junk
                # data we'll write into the Application.
                data = None

            if data == "[deleted]":
                # Translators: This text is displayed to users when the user has chosen to restrict data and is trying to apply for multiple partners
                fail_msg = _("This field consists only of restricted text.")
                form.add_error(label, fail_msg)
                return self.form_invalid(form)

            if data:
                setattr(app, field, data)

        app.save()

        # And clean up the session so as not to confuse future applications.
        del self.request.session[PARTNERS_SESSION_KEY]

        return super().form_valid(form)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Local functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def _get_partner_fields(self, partner):
        """
        Return a list of the partner-specific data fields required by the given
        Partner.

        Parameters
        ----------
        partner : Partner
            Partner object

        Returns
        -------
        list
            An array of field names that are required in the application form
        """
        return [
            field for field in PARTNER_FORM_OPTIONAL_FIELDS if getattr(partner, field)
        ]

    def _get_user_fields(self, partner):
        """
        Return a dict of user-specific data fields required by one Partner to whom
        the user is requesting access.

        Parameters
        ----------
        partner : Partner
            Partner object

        Returns
        -------
        dict
            A dictionary with the fields that are required
        """
        needed_fields = {}
        for field in USER_FORM_FIELDS:
            if getattr(partner, field):  # Will be True if required by Partner.
                needed_fields[field] = True

        return needed_fields

    def _get_partner(self):
        partner_id = self.kwargs["pk"]
        self.request.session[PARTNERS_SESSION_KEY] = partner_id
        partner = get_object_or_404(Partner, id=self.kwargs["pk"])

        return partner

    def _check_duplicate_applications(self, partner):
        """
        Disallow a user from applying to the same partner more than once

        Parameters
        ----------
        partner : Partner
            Partner object

        Returns
        -------
        bool
            A boolean value to indicate whether an application is a duplicate or not
        """
        # if partner is collection or has specific title then
        # multiple applications are allowed
        if partner.specific_title:
            return False

        editor = Editor.objects.get(user=self.request.user)
        # get duplicate applications
        apps = Application.objects.filter(
            partner=partner,
            editor=editor,
            status__in=(
                Application.QUESTION,
                Application.PENDING,
                Application.APPROVED,
            ),
        )
        if apps.exists():
            # Translators: This message is shown to user when he tries to apply to same partner more than once
            message = _("You already have an application for this Partner.")
            if len(apps) == 1:
                # if there is only one application then redirect user to that application
                app = apps[0]
                url = reverse("applications:evaluate", kwargs={"pk": app.id})
            else:
                # if there are more than one application exists then
                # redirect the user to my_applications page
                url = reverse("users:my_applications", kwargs={"pk": editor.pk})
            return (url, message)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        partner = self._get_partner()
        context["partner"] = partner
        context["EMAIL"] = Partner.EMAIL

        return context


class _BaseListApplicationView(CoordinatorsOnly, ToURequired, ListView):
    """
    Factors out shared functionality for the application list views. Not
    intended to be user-facing. Subclasses should implement get_queryset().
    """

    model = Application

    def _filter_queryset(self, base_qs, editor, partner):
        """
        Handle filters that might have been passed in by post().
        """
        if editor:
            base_qs = base_qs.filter(editor=editor)

        if partner:
            base_qs = base_qs.filter(partner=partner)

        return base_qs

    def _set_object_list(self, filters):
        # If the view lets users apply filters to the queryset, this is where
        # the filtered queryset can be set as the object_list for the view.
        # If the view doesn't have filters, or the user hasn't applied them,
        # this applies default Django behavior.
        base_qs = self.get_queryset()
        if filters:
            editor = filters[0]["object"]
            partner = filters[1]["object"]
            self.object_list = self._filter_queryset(
                base_qs=base_qs, editor=editor, partner=partner
            )
        else:
            self.object_list = base_qs

    def get_queryset(self):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        """
        Subclasses should call super on this and add title, include_template (if
        different from the default), and any other context specific to that
        subclass. If you add pages, be sure to expand the button menu, and tell
        the context which page is currently active.
        """
        # We need to determine self.object_list *before* we do the call to
        # super below, because it will expect self.object_list to be defined.
        # Our object_list varies depending on whether the user has filtered the
        # queryset.
        filters = kwargs.pop("filters", None)

        # If the POST data didn't have an editor, try the GET data.
        # The user might be going through paginated data.
        # There is almost certainly a better way to do this, since we're
        # recreating a data structure from post.
        if not filters:
            try:
                editor_pk = urllib.parse.unquote(
                    bleach.clean(self.request.GET.get("Editor"))
                )
                if editor_pk:
                    editor = Editor.objects.get(pk=editor_pk)
                else:
                    editor = ""

                partner_pk = urllib.parse.unquote(
                    bleach.clean(self.request.GET.get("Partner"))
                )
                if partner_pk:
                    partner = Partner.objects.get(pk=partner_pk)
                else:
                    partner = ""

                filters = [
                    # Translators: Editor = wikipedia editor, gender unknown.
                    {"label": _("Editor"), "object": editor},
                    # Translators: Partner is the resource a user will access.
                    {"label": _("Partner"), "object": partner},
                ]
            except:
                logger.info("Unable to set filter from GET data.")
                pass

        self._set_object_list(filters)

        context = super(_BaseListApplicationView, self).get_context_data(**kwargs)

        context["filters"] = filters

        context["object_list"] = self.object_list
        # Set up pagination.
        paginator = Paginator(self.object_list, 20)
        page = self.request.GET.get("page")
        try:
            applications = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            applications = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            applications = paginator.page(paginator.num_pages)

        context["object_list"] = applications

        # Set up button group menu.
        context["approved_url"] = reverse_lazy("applications:list_approved")
        context["rejected_url"] = reverse_lazy("applications:list_rejected")
        context["renewal_url"] = reverse_lazy("applications:list_renewal")
        context["pending_url"] = reverse_lazy("applications:list")
        context["sent_url"] = reverse_lazy("applications:list_sent")

        # Add miscellaneous page contents.
        context["include_template"] = "applications/application_list_include.html"

        context["autocomplete_form"] = ApplicationAutocomplete(user=self.request.user)

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles filters applied by the autocomplete form, limiting the queryset
        and redisplaying the text. The self.render_to_response() incantation is
        borrowed from django's form_invalid handling.
        """
        try:
            # request.POST['editor'] will be the pk of an Editor instance, if
            # it exists.
            editor = Editor.objects.get(pk=request.POST["editor"])
        except (KeyError, ValueError):
            # The user didn't filter by editor, and that's OK.
            editor = None
        except Editor.DoesNotExist:
            # The format call is guaranteed to work, because if we got here we
            # *don't* have a KeyError.
            logger.exception(
                "Autocomplete requested editor #{pk}, who does "
                "not exist".format(pk=request.POST["editor"])
            )
            raise

        try:
            partner = Partner.objects.get(pk=request.POST["partner"])
        except (KeyError, ValueError):
            # The user didn't filter by partner, and that's OK.
            partner = None
        except Partner.DoesNotExist:
            logger.exception(
                "Autocomplete requested partner #{pk}, who does "
                "not exist".format(pk=request.POST["partner"])
            )
            raise

        filters = [
            # Translators: Editor = wikipedia editor, gender unknown.
            {"label": _("Editor"), "object": editor},
            # Translators: Partner is the resource a user will access.
            {"label": _("Partner"), "object": partner},
        ]

        return self.render_to_response(self.get_context_data(filters=filters))


class ListApplicationsView(_BaseListApplicationView):
    def get_queryset(self, **kwargs):
        """
        List only the open applications from available partners: that makes this
        page useful as a reviewer queue. Approved and rejected applications
        should be listed elsewhere: kept around for historical reasons, but kept
        off the main page to preserve utility (and limit load time).
        """
        if self.request.user.is_superuser:
            base_qs = (
                Application.objects.filter(
                    ~Q(partner__authorization_method=Partner.BUNDLE),
                    status__in=[Application.PENDING, Application.QUESTION],
                    partner__status__in=[Partner.AVAILABLE, Partner.WAITLIST],
                    editor__isnull=False,
                )
                .exclude(editor__user__groups__name="restricted")
                .order_by("status", "partner", "date_created")
            )

        else:
            base_qs = (
                Application.objects.filter(
                    ~Q(partner__authorization_method=Partner.BUNDLE),
                    status__in=[Application.PENDING, Application.QUESTION],
                    partner__status__in=[Partner.AVAILABLE, Partner.WAITLIST],
                    partner__coordinator__pk=self.request.user.pk,
                    editor__isnull=False,
                )
                .exclude(editor__user__groups__name="restricted")
                .order_by("status", "partner", "date_created")
            )

        return base_qs

    def get_context_data(self, **kwargs):
        context = super(ListApplicationsView, self).get_context_data(**kwargs)
        # Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Pending' applications.
        context["title"] = _("Applications to review")

        context[
            "include_template"
        ] = "applications/application_list_reviewable_include.html"

        # For constructing the dropdown in the batch editing form.
        context["status_choices"] = Application.STATUS_CHOICES

        context["pending_class"] = "active"

        return context


class ListApprovedApplicationsView(_BaseListApplicationView):
    def get_queryset(self):
        if self.request.user.is_superuser:
            return (
                Application.objects.filter(
                    ~Q(partner__authorization_method=Partner.BUNDLE),
                    status=Application.APPROVED,
                    editor__isnull=False,
                )
                .exclude(editor__user__groups__name="restricted")
                .order_by("status", "partner", "date_created")
            )
        else:
            return (
                Application.objects.filter(
                    ~Q(partner__authorization_method=Partner.BUNDLE),
                    status=Application.APPROVED,
                    partner__coordinator__pk=self.request.user.pk,
                    editor__isnull=False,
                )
                .exclude(editor__user__groups__name="restricted")
                .order_by("status", "partner", "date_created")
            )

    def get_context_data(self, **kwargs):
        context = super(ListApprovedApplicationsView, self).get_context_data(**kwargs)
        # Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Approved' applications.
        context["title"] = _("Approved applications")

        context["approved_class"] = "active"

        return context


class ListRejectedApplicationsView(_BaseListApplicationView):
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.include_invalid.filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status__in=[Application.NOT_APPROVED, Application.INVALID],
                editor__isnull=False,
            ).order_by("date_closed", "partner")
        else:
            return Application.include_invalid.filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status__in=[Application.NOT_APPROVED, Application.INVALID],
                partner__coordinator__pk=self.request.user.pk,
                editor__isnull=False,
            ).order_by("date_closed", "partner")

    def get_context_data(self, **kwargs):
        context = super(ListRejectedApplicationsView, self).get_context_data(**kwargs)
        # Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Rejected' applications.
        context["title"] = _("Rejected applications")

        context["rejected_class"] = "active"

        return context


class ListRenewalApplicationsView(_BaseListApplicationView):
    """
    Lists access grants that users have requested, but not received, renewals
    for.
    """

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.objects.filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status__in=[Application.PENDING, Application.QUESTION],
                parent__isnull=False,
                editor__isnull=False,
            ).order_by("-date_created")
        else:
            return Application.objects.filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status__in=[Application.PENDING, Application.QUESTION],
                partner__coordinator__pk=self.request.user.pk,
                parent__isnull=False,
                editor__isnull=False,
            ).order_by("-date_created")

    def get_context_data(self, **kwargs):
        context = super(ListRenewalApplicationsView, self).get_context_data(**kwargs)

        # Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Up for renewal' applications.
        context["title"] = _("Access grants up for renewal")

        context["renewal_class"] = "active"

        return context


class ListSentApplicationsView(_BaseListApplicationView):
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.objects.filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status=Application.SENT,
                editor__isnull=False,
            ).order_by("date_closed", "partner")
        else:
            return Application.objects.filter(
                ~Q(partner__authorization_method=Partner.BUNDLE),
                status=Application.SENT,
                partner__coordinator__pk=self.request.user.pk,
                editor__isnull=False,
            ).order_by("date_closed", "partner")

    def get_context_data(self, **kwargs):
        context = super(ListSentApplicationsView, self).get_context_data(**kwargs)
        # Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Sent' applications.
        context["title"] = _("Sent applications")

        context["sent_class"] = "active"

        return context


class EvaluateApplicationView(
    NotDeleted, PartnerCoordinatorOrSelf, ToURequired, UpdateView
):
    """
    Allows Coordinators to:
    * view single applications
    * view associated editor metadata
    * assign status
    * view recent applications made by applicant
    """

    model = Application
    fields = ["status"]
    template_name_suffix = "_evaluation"
    success_url = reverse_lazy("applications:list")

    def form_valid(self, form):
        app = self.object
        status = form.cleaned_data["status"]

        # The logic below hard limits coordinators from approving applications when a particular proxy partner has run out of accounts.
        if is_proxy_and_application_approved(status, app):
            if app.partner.status == Partner.WAITLIST:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    # fmt: off
                    # Translators: After a coordinator has changed the status of an application to APPROVED, if the corresponding partner/collection is waitlisted this message appears.
                    _("Cannot approve application as partner with proxy authorization method is waitlisted."),
                    # fmt: on
                )
                return HttpResponseRedirect(
                    reverse("applications:evaluate", kwargs={"pk": self.object.pk})
                )

            total_accounts_available_for_distribution = get_accounts_available(app)
            if total_accounts_available_for_distribution is None:
                pass
            elif total_accounts_available_for_distribution > 0:
                # We manually send a signal to waitlist the concerned partner if we've only one account available.
                # This could be tweaked in the future to also waitlist partners with collections. We don't do that
                # now since it's possible we have accounts left for distribution on other collections.
                if total_accounts_available_for_distribution == 1:
                    no_more_accounts.send(
                        sender=self.__class__, partner_pk=app.partner.pk
                    )
            else:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    # fmt: off
                    # Translators: After a coordinator has changed the status of an application to APPROVED, if the corresponding partner/collection has no accounts for distribution, this message appears.
                    _("Cannot approve application as partner with proxy authorization method is waitlisted and (or) has zero accounts available for distribution."),
                    # fmt: on
                )
                return HttpResponseRedirect(
                    reverse("applications:evaluate", kwargs={"pk": self.object.pk})
                )

        # Correctly assign sent_by.
        if app.status == Application.SENT or (
            app.is_instantly_finalized() and app.status == Application.APPROVED
        ):
            app.sent_by = self.request.user
            app.save()

        with reversion.create_revision():
            reversion.set_user(self.request.user)
            try:
                return super(EvaluateApplicationView, self).form_valid(form)
            except IntegrityError:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    # Translators: This message appears on an "access denied" screen that stops users who attempt to authorize an editor to access a resource during a time period for which they are already authorized.
                    _("You attempted to create a duplicate authorization."),
                )
                raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super(EvaluateApplicationView, self).get_context_data(**kwargs)
        context["editor"] = self.object.editor
        context["versions"] = Version.objects.get_for_object(self.object)

        app = self.object

        # We show accounts available for partners/collections in the evaluation page
        context["total_accounts_available_for_distribution"] = get_accounts_available(
            app
        )

        # Check if the person viewing this application is actually this
        # partner's coordinator, and not *a* coordinator who happens to
        # have applied, or a superuser.
        partner_coordinator = self.request.user == self.object.partner.coordinator
        superuser = self.request.user.is_superuser
        context["partner_coordinator"] = partner_coordinator or superuser
        existing_authorization = app.get_authorization()
        if app.parent and existing_authorization:
            context["previous_auth_expiry_date"] = existing_authorization.date_expires

        # Add recent applications in context
        # get applications opened by editor in last 3 months
        # also exclude current app if it is present in recent apps

        recent_apps = (
            Application.objects.filter(
                editor=self.object.editor,
                date_created__gte=datetime.today() - timedelta(days=90),
            )
            .exclude(pk=app.pk)
            .order_by("-id")
        )
        context["recent_apps"] = recent_apps

        return context

    def get_form(self, form_class=None):
        app = self.get_object()
        # Status cannot be changed for applications made to bundle partners.
        if app.partner.authorization_method == Partner.BUNDLE:
            bundle_url = reverse("about")
            library_url = reverse("users:my_library")
            contact_url = reverse("contact")
            messages.add_message(
                self.request,
                messages.WARNING,
                # fmt: off
                # Translators: This message is shown to users when they access an application page of a now Bundle partner (new applications aren't allowed for Bundle partners and the status of old applications cannot be modified)
                _("This application cannot be modified since this partner is now part of our <a href='{bundle}'>bundle access</a>. If you are eligible, you can access this resource from <a href='{library}'>your library</a>. <a href='{contact}'>Contact us</a> if you have any questions.")
                .format(bundle=bundle_url, library=library_url, contact=contact_url),
                # fmt: on
            )
            return
        if form_class is None:
            form_class = self.form_class
        form = super(EvaluateApplicationView, self).get_form(form_class)

        form.helper = FormHelper()
        # Set a form ID to make it easier to test
        form.helper.form_id = "set-status-form"
        form.helper.add_input(
            Submit(
                "submit",
                # Translators: this lets a reviewer set the status of a single application.
                _("Set application status"),
                css_class="twl-btn",
            )
        )

        app = self.get_object()
        if app.is_instantly_finalized():
            status_choices = Application.STATUS_CHOICES[:]
            status_choices.pop(4)
            form.fields["status"].choices = status_choices

        if app.editor.user == self.request.user:
            if more_applications_than_accounts_available(app):
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    # fmt: off
                    # Translators: This warning is message is shown to applicants when the number of pending applications is greater than the number of accounts available.
                    _("There are more pending applications than available accounts. Your application might get waitlisted."),
                    # fmt: on
                )

        return form

    def post(self, request, *args, **kwargs):
        app = self.get_object()
        if app.status == Application.INVALID:
            messages.add_message(
                self.request,
                messages.ERROR,
                # Translators: this message is shown to coordinators who attempt to change an application's Status from INVALID to any other Status.
                _("Status of INVALID applications cannot be changed."),
            )
            return HttpResponseRedirect(
                reverse("applications:evaluate", kwargs={"pk": app.pk})
            )
        return super(EvaluateApplicationView, self).post(request, *args, **kwargs)


class BatchEditView(CoordinatorsOnly, ToURequired, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            assert "batch_status" in request.POST

            status = int(request.POST["batch_status"])
            assert status in [
                Application.PENDING,
                Application.QUESTION,
                Application.APPROVED,
                Application.NOT_APPROVED,
                Application.SENT,
                Application.INVALID,
            ]
        except (AssertionError, ValueError):
            # ValueError will be raised if the status cannot be cast to int.
            logger.exception("Did not find valid data for batch editing")
            return HttpResponseBadRequest()

        try:
            assert "applications" in request.POST
        except AssertionError:
            messages.add_message(
                self.request,
                messages.WARNING,
                # Translators: When a coordinator is batch editing (https://wikipedialibrary.wmflabs.org/applications/list/), they receive this message if they click Set Status without selecting any applications.
                _("Please select at least one application."),
            )
            return HttpResponseRedirect(reverse("applications:list"))

        # IMPORTANT! It would be tempting to just do QuerySet.update() here,
        # but that does NOT send the pre_save signal, which is doing some
        # important work for Applications. This includes handling the closing
        # dates for applications and sending email notifications to editors
        # about their applications.

        # This might seem a tad complicated/overkill, but we need this in order to
        # stop batch approvals of applications for proxy partners when accounts for
        # approval are greater than the number of accounts available.
        batch_update_failed = []
        batch_update_success = []
        partners_distribution_flag = {}

        applications_per_partner = {}
        waitlist_dict = {}
        all_apps = request.POST.getlist("applications")
        for each_app_pk in all_apps:
            try:
                each_app = Application.objects.get(pk=each_app_pk)
            except Application.DoesNotExist:
                logger.exception(
                    "Could not find app with posted pk {pk}; "
                    "continuing through remaining apps".format(pk=each_app_pk)
                )
                continue
            # We loop through the list of applications (only proxy) counting the number of applications that
            # are to be approved for a particular partner or collection. The counts are then updated in
            # applications_per_partner dictionary depending on the application type.
            if is_proxy_and_application_approved(status, app=each_app):
                app_count = applications_per_partner.get(each_app.partner.pk)
                if app_count is None:
                    applications_per_partner[each_app.partner.pk] = 1
                else:
                    applications_per_partner[each_app.partner.pk] += 1

        # For applications that are for partners, we get the number of accounts available based
        # on their valid authorizations to ensure we have enough accounts available and set the
        # boolean value for the corresponding partner_pk in the partners_distribution_flag dictionary.
        for partner_pk, app_count in applications_per_partner.items():
            total_accounts_available = Partner.objects.filter(pk=partner_pk).values(
                "accounts_available"
            )[0]["accounts_available"]
            if total_accounts_available is not None:
                valid_authorizations = count_valid_authorizations(partner_pk)
                total_accounts_available_for_distribution = (
                    total_accounts_available - valid_authorizations
                )
                if app_count > total_accounts_available_for_distribution:
                    partners_distribution_flag[partner_pk] = False
                elif app_count == total_accounts_available_for_distribution:
                    # The waitlist_dict keeps track of partners that'll
                    # run out of accounts once we approve all the applications.
                    waitlist_dict[partner_pk] = True
                    partners_distribution_flag[partner_pk] = True
                else:
                    partners_distribution_flag[partner_pk] = True
            else:
                partners_distribution_flag[partner_pk] = True

        for app_pk in all_apps:
            try:
                app = Application.objects.get(pk=app_pk)
            except Application.DoesNotExist:
                continue

            # Based on the distribution flags, we either mark applications as approved and update the batch_update_success
            # list with the application id or do nothing and update the batch_update_failed list.
            if is_proxy_and_application_approved(status, app):
                if app.partner.status != Partner.WAITLIST:
                    if partners_distribution_flag[app.partner.pk] is True:
                        batch_update_success.append(app_pk)
                        app.status = status
                        app.sent_by = request.user
                        app.save()
                    else:
                        batch_update_failed.append(app_pk)
                else:
                    batch_update_failed.append(app_pk)
            else:
                batch_update_success.append(app_pk)
                app.status = status
                if (
                    app.is_instantly_finalized() and app.status == Application.APPROVED
                ) or app.status == Application.SENT:
                    app.sent_by = request.user
                app.save()

        # We manually send the signals to waitlist the partners with corresponding 'True' values.
        # This could be tweaked in the future to also waitlist partners with collections. We don't do that
        # now since it's possible we have accounts left for distribution on other collections.
        for partner_pk in waitlist_dict:
            no_more_accounts.send(sender=self.__class__, partner_pk=partner_pk)

        if batch_update_success:
            success_apps = ", ".join(map(str, batch_update_success))
            messages.add_message(
                request,
                messages.SUCCESS,
                # Translators: After a coordinator has changed the status of a number of applications, this message appears.
                _("Batch update of application(s) {} successful.").format(success_apps),
            )
        if batch_update_failed:
            failed_apps = ", ".join(map(str, batch_update_failed))
            messages.add_message(
                request,
                messages.ERROR,
                # fmt: off
                # Translators: After a coordinator has changed the status of a number of applications to APPROVED, if the corresponding partner(s) is/are waitlisted or has no accounts for distribution, this message appears.
                _("Cannot approve application(s) {} as partner(s) with proxy authorization method is/are waitlisted and (or) has/have not enough accounts available. If not enough accounts are available, prioritise the applications and then approve applications equal to the accounts available.")
                .format(failed_apps),
                # fmt: on
            )

        return HttpResponseRedirect(reverse_lazy("applications:list"))


class ListReadyApplicationsView(CoordinatorsOnly, ListView):
    template_name = "applications/send.html"

    def get_queryset(self):
        # Find all approved applications, then list the relevant partners.
        # Don't include applications from restricted users when generating
        # this list.
        base_queryset = Application.objects.filter(
            status=Application.APPROVED, editor__isnull=False
        ).exclude(editor__user__groups__name="restricted")

        partner_list = Partner.objects.filter(
            applications__in=base_queryset,
            authorization_method__in=[Partner.CODES, Partner.EMAIL],
        ).distinct()

        # Superusers can see all unrestricted applications, otherwise
        # limit to ones from the current coordinator
        if self.request.user.is_superuser:
            return partner_list
        else:
            return partner_list.filter(coordinator__pk=self.request.user.pk)


class SendReadyApplicationsView(PartnerCoordinatorOnly, DetailView):
    model = Partner
    template_name = "applications/send_partner.html"

    def dispatch(self, request, *args, **kwargs):
        partner = self.get_object()
        auth_method = partner.authorization_method
        if auth_method == Partner.EMAIL or auth_method == Partner.CODES:
            return super(SendReadyApplicationsView, self).dispatch(
                request, *args, **kwargs
            )
        else:
            raise Http404("Applications for this Partner are sent automatically")

    def get_context_data(self, **kwargs):
        context = super(SendReadyApplicationsView, self).get_context_data(**kwargs)
        partner = self.get_object()
        apps = partner.applications.filter(
            status=Application.APPROVED, editor__isnull=False
        ).exclude(editor__user__groups__name="restricted")
        app_outputs = {}

        for app in apps:
            app_outputs[app] = get_output_for_application(app)

        context["app_outputs"] = app_outputs

        # Supports send_partner template with total approved/sent applications.
        total_apps_approved = Application.objects.filter(
            partner=partner, status=Application.APPROVED
        ).count()

        total_apps_sent = Application.objects.filter(
            partner=partner, status=Application.SENT
        ).count()

        total_apps_approved_or_sent = total_apps_approved + total_apps_sent

        # Provide context to template only if accounts_available field is set
        if partner.accounts_available is not None:
            context["total_apps_approved_or_sent"] = total_apps_approved_or_sent

        else:
            context["total_apps_approved_or_sent"] = None

        available_access_codes = AccessCode.objects.filter(
            partner=partner, authorization__isnull=True
        )
        context["available_access_codes"] = available_access_codes

        return context

    def post(self, request, *args, **kwargs):
        if self.get_object().authorization_method == Partner.EMAIL:
            try:
                request.POST["applications"]
            except KeyError:
                logger.exception("Posted data is missing required parameter")
                return HttpResponseBadRequest()

            # Use getlist, don't just access the POST dictionary value using
            # the 'applications' key! If you just access the dict element you will
            # end up treating it as a string - thus if the pk of 80 has been
            # submitted, you will end up filtering for pks in [8, 0] and nothing
            # will be as you expect. getlist will give you back a list of items
            # instead of a string, and then you can use it as desired.
            app_pks = request.POST.getlist("applications")

            for app_pk in app_pks:
                try:
                    application = self.get_object().applications.get(pk=app_pk)
                    application.status = Application.SENT
                    application.sent_by = request.user
                    application.save()
                except ValueError:
                    # This will be raised if something that isn't a number gets posted
                    # as an app pk.
                    logger.exception("Invalid value posted")
                    return HttpResponseBadRequest()
                except ObjectDoesNotExist:
                    # It would be odd that this situation should arise outside
                    # of tests, but we should handle it there at least.
                    continue

        elif self.get_object().authorization_method == Partner.CODES:
            try:
                request.POST["accesscode"]
            except KeyError:
                logger.exception("Posted data is missing required parameter")
                return HttpResponseBadRequest()

            select_outputs = request.POST.getlist("accesscode")
            # The form returns "{{ app_pk }}_{{ access_code }}" for every selected
            # application so that we can associate each code with its application.
            send_outputs = [
                (output.split("_")[0], output.split("_")[1])
                for output in select_outputs
                if output != "default"
            ]

            # Make sure the coordinator hasn't selected the same code
            # multiple times.
            all_codes = [output[1] for output in send_outputs]
            if len(all_codes) > len(set(all_codes)):
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    # Translators: This message is shown to coordinators who attempt to assign the same access code to multiple users.
                    _("Error: Code used multiple times."),
                )
                return HttpResponseRedirect(
                    reverse(
                        "applications:send_partner", kwargs={"pk": self.get_object().pk}
                    )
                )

            for send_output in send_outputs:
                app_pk = send_output[0]
                app_code = send_output[1]

                application = Application.objects.get(pk=app_pk)
                code_object = AccessCode.objects.get(
                    code=app_code, partner=application.partner
                )

                application.status = Application.SENT
                application.sent_by = request.user
                application.save()

                # Access code object needs to be updated after the application
                # to ensure that the authorization object has been created.
                # This filtering should only ever find one object. There will
                # always be a user and partner
                auth = Authorization.objects.get(
                    user=application.user, partners=application.partner
                )
                if hasattr(auth, "accesscodes"):
                    if auth.accesscodes:
                        logger.info(
                            "Authorization already has an access code, reassigning it...."
                        )
                        # Get old access code and delete it
                        old_access_code = AccessCode.objects.get(pk=auth.accesscodes.pk)
                        old_access_code.delete()
                        auth.accesscodes = code_object
                        auth.save()
                        code_object.authorization = auth
                    else:
                        code_object.authorization = auth
                else:
                    code_object.authorization = auth

                code_object.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            # Translators: After a coordinator has marked a number of applications as 'sent', this message appears.
            _("All selected applications have been marked as sent."),
        )

        return HttpResponseRedirect(
            reverse("applications:send_partner", kwargs={"pk": self.get_object().pk})
        )


class RenewApplicationView(SelfOnly, ToURequired, DataProcessingRequired, FormView):
    """
    This view takes an existing Application and creates a clone, with new
    dates and a FK back to the original application. If the application is
    made to a proxy partner, and (or) if the account_email field is true,
    tries to get the account length preference and (or) the email from the
    user respectively. If not, just adds an additional confirmation step.
    """

    model = Application
    template_name = "applications/confirm_renewal.html"
    form_class = RenewalForm

    def dispatch(self, request, *args, **kwargs):
        app = self.get_object()

        if app.partner.is_not_available:
            return_url = self._set_return_url(self._get_return_url())
            messages.add_message(
                request,
                messages.WARNING,
                # fmt: off
                # Translators: When a user tries to renew their resource, they receive this message if the partner is not available.
                _("Cannot renew application at this time as partner is not available. Please check back later, or contact us for more information."),
                # fmt: on
            )
            return HttpResponseRedirect(return_url)
        elif app.partner.status == Partner.WAITLIST:
            messages.add_message(
                request,
                messages.WARNING,
                # fmt: off
                # Translators: When a user renews their resource, they receive this message if none are currently available. They are instead placed on a 'waitlist' for later approval.
                _("This partner does not have any access grants available at this time. You may still apply for access; your application will be reviewed when access grants become available."),
                # fmt: on
            )

        return super(RenewApplicationView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        app = Application.objects.get(pk=self.kwargs["pk"])

        if app.partner.authorization_method == Partner.BUNDLE:
            raise PermissionDenied

        try:
            assert (app.status == Application.APPROVED) or (
                app.status == Application.SENT
            )
        except AssertionError:
            logger.exception(
                "Attempt to renew unapproved app #{pk} has been "
                "denied".format(pk=app.pk)
            )
            messages.add_message(
                self.request,
                messages.WARNING,
                # fmt: off
                # Translators: This message is displayed when an attempt by a user to renew an application has been denied for some reason.
                _("Attempt to renew unapproved application #{pk} has been denied")
                .format(pk=app.pk),
                # fmt: on
            )
            raise PermissionDenied

        return app

    def get_context_data(self, **kwargs):
        context = super(RenewApplicationView, self).get_context_data(**kwargs)
        context["partner"] = self.get_object().partner
        return context

    def _get_return_url(self):
        # Figure out where users should be returned to.
        return_url = reverse("users:home")  # set default
        try:
            return_url = self.request.META["HTTP_REFERER"]
        except KeyError:
            # If we don't have an HTTP_REFERER, we'll use the default.
            pass
        return return_url

    def _set_return_url(self, referer):
        # We'll validate the return_url set in the previous method
        return_url = reverse("users:home")  # default
        domain = urlparse(referer).netloc
        if domain in settings.ALLOWED_HOSTS:
            return_url = referer
        return return_url

    def get_form(self, form_class=None):
        return_url = self._get_return_url()
        if form_class is None:
            form_class = self.form_class

        kwargs = self.get_form_kwargs()

        # In order to dynamically set the fields, we'll have to
        # send the fields we require via kwargs as field_params
        field_params = {}
        application = self.get_object()
        partner = application.partner
        if partner.account_email:
            field_params["account_email"] = application.account_email
        if partner.requested_access_duration:
            field_params["requested_access_duration"] = None
        field_params["return_url"] = return_url

        kwargs["field_params"] = field_params
        return form_class(**kwargs)

    def form_valid(self, form):
        referer = form.cleaned_data["return_url"]
        return_url = self._set_return_url(referer)

        application = self.get_object()
        partner = application.partner
        if partner.account_email:
            application.account_email = form.cleaned_data["account_email"]
        if partner.requested_access_duration:
            application.requested_access_duration = form.cleaned_data[
                "requested_access_duration"
            ]

        renewal = application.renew()

        # Requesting Renewing invalidates the my_library cache
        # This happens regardless of sucess so that the message will be displayed
        self.request.user.userprofile.delete_my_library_cache()

        if not renewal:
            messages.add_message(
                self.request,
                messages.WARNING,
                # fmt: off
                # Translators: If a user requests the renewal of their account, but it wasn't renewed, this message is shown to them.
                _("This object cannot be renewed. (This probably means that you have already requested that it be renewed.)"),
                # fmt: on
            )
            return HttpResponseRedirect(return_url)

        messages.add_message(
            self.request,
            messages.INFO,
            # fmt: off
            # Translators: If a user requests the renewal of their account, this message is shown to them.
            _("Your renewal request has been received. A coordinator will review your request."),
            # fmt: on
        )

        return HttpResponseRedirect(return_url)
