import bleach
import datetime
import json
import logging
from datetime import date, timedelta

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django.db.models import Q
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy, resolve, Resolver404, reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateView, View, RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, FormView, DeleteView
from django.views.generic.list import ListView
from django.utils.cache import learn_cache_key
from django.utils.decorators import classonlymethod, method_decorator
from django.utils.http import is_safe_url
from django.utils.translation import gettext_lazy as _
from django_comments.models import Comment
from django.utils import timezone
from django.utils.translation import get_language

from TWLight.resources.filters import PartnerFilter
from TWLight.resources.helpers import get_partner_description, get_tag_names
from TWLight.resources.models import Partner, PartnerLogo, PhabricatorTask
from TWLight.view_mixins import (
    PartnerCoordinatorOrSelf,
    SelfOnly,
    test_func_coordinators_only,
)
from TWLight.users.groups import get_coordinators, get_restricted
from TWLight.users.helpers.authorizations import get_valid_partner_authorizations
from TWLight.users.helpers.editor_data import editor_bundle_eligible

from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from reversion.models import Version

from .forms import (
    EditorUpdateForm,
    SetLanguageForm,
    TermsForm,
    EmailChangeForm,
    RestrictDataForm,
    UserEmailForm,
    CoordinatorEmailForm,
)
from .helpers.authorizations import sort_authorizations_into_resource_list
from .models import Editor, UserProfile, Authorization
from .serializers import FavoriteCollectionSerializer, UserSerializer
from TWLight.applications.models import Application

logger = logging.getLogger(__name__)

# Build an empty response object
vary_response = HttpResponse()
# Add the same vary header used in the `vary_on_headers` decorator
vary_response["Vary"] = "Accept-Language, Cookie"


def _is_real_url(url):
    """
    Users might have altered the URL parameters. Let's not just blindly
    redirect; let's actually make sure we can get somewhere first.
    """
    try:
        resolve(url)
        return True
    except Resolver404:
        return False


def _build_task_state(phab_task_qs):
    task_list = []
    disabled = False
    for task in phab_task_qs:
        if task.task_type == 2:
            disabled = True
        task_list.append(
            {
                "id": str(task.phabricator_task),
                "severity": str(task.task_display[1]),
                "display": str(task.task_display[0]),
                "help": str(task.task_display[2]),
                "url": str(task.url),
            }
        )
    return task_list, disabled


def _redirect_to_next_param(request):
    next_param = request.GET.get(REDIRECT_FIELD_NAME, "")
    if (
        next_param
        and is_safe_url(url=next_param, allowed_hosts=request.get_host())
        and _is_real_url(next_param)
    ):
        return next_param
    else:
        return reverse_lazy("users:my_library")


class UserDetailView(SelfOnly, TemplateView):
    template_name = "users/user_detail.html"

    def get_object(self):
        """
        Although 'user' is part of the default context, we need to define a
        get_object in order to be able to use the SelfOnly mixin.
        """
        assert "pk" in list(self.kwargs.keys())

        try:
            if self.kwargs["pk"] == None:
                return User.objects.get(self.kwargs["pk"])
            return User.objects.get(pk=self.kwargs["pk"])
        except User.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        user = User.objects.select_related("userprofile").get(pk=self.request.user.pk)
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context["language_form"] = SetLanguageForm(user=user)
        context["password_form"] = PasswordChangeForm(user=user)
        context["terms_form"] = TermsForm(user_profile=user.userprofile)
        return context


class EditorDetailView(PartnerCoordinatorOrSelf, DetailView):
    """
    User profile data page for users who are Editors. Uses the Editor model,
    because:
    1) That's where most of the data is;
    2) Using the Editor model means its URL parameter is consistent with that of
       EditorUpdateView, because you know Wikipedians will employ URL hacking
       to get places on the site, and this simplifies that.
    """

    model = Editor
    template_name = "users/editor_detail.html"

    def get_context_data(self, **kwargs):
        context = super(EditorDetailView, self).get_context_data(**kwargs)
        user = self.request.user
        editor = user.editor
        context["editor"] = editor  # allow for more semantic templates
        context["form"] = EditorUpdateForm(instance=editor)
        context["language_form"] = SetLanguageForm(user=user)
        context["email_form"] = UserEmailForm(user=user)
        # Check if the user is in the group: 'coordinators',
        # and add the reminder email preferences form.
        if test_func_coordinators_only(user):
            context["coordinator_email_form"] = CoordinatorEmailForm(user=user)

        try:
            if user.editor == editor and not editor.contributions:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    # fmt: off
                    # Translators: This message is shown on user's own profile page, encouraging them to make sure their information is up to date, so that account coordinators can use the information to judge applications.
                    _("Please <a class='twl-links' href='{url}'>update your contributions</a> to Wikipedia to help coordinators evaluate your applications.")
                    .format(
                        url=reverse_lazy(
                        "users:editor_update", kwargs={"pk": editor.pk}
                        )
                    ),
                    # fmt: on
                )
        except Editor.DoesNotExist:
            """
            If the user viewing the site does not have an attached editor
            (which can happen for administrative users), this error will be
            thrown, preventing the user from viewing the site. We don't actually
            want to have a 500 in this case, though; we just want to not add the
            message, and move on.
            """
            pass

        context["password_form"] = PasswordChangeForm(user=user)
        context["terms_form"] = TermsForm(user_profile=user.userprofile)

        return context

    def post(self, request, *args, **kwargs):
        editor = self.get_object()
        if "download" in request.POST:
            # When users click the Download button in the Data section of
            # their user page, provide a json with any personal information
            # they submitted to the site.

            user_json = {}
            editor_data = Editor.objects.get(pk=editor.pk)

            user_json["user_data"] = {}
            user_field_list = [
                "wp_username",
                "contributions",
                "real_name",
                "country_of_residence",
                "occupation",
                "affiliation",
            ]
            for field in user_field_list:
                field_data = getattr(editor_data, field)
                if field_data:
                    user_json["user_data"][field] = field_data

            user_apps = Application.objects.filter(editor=editor)
            user_json["applications"] = {}
            for app in user_apps:
                user_json["applications"][app.id] = {}
                for field in ["rationale", "comments", "account_email"]:
                    field_data = getattr(app, field)
                    if field_data:
                        user_json["applications"][app.id][field] = field_data

            user_comments = Comment.objects.filter(user_id=editor.user.id)
            user_json["comments"] = []
            for comment in user_comments:
                user_json["comments"].append(comment.comment)

            json_data = json.dumps(user_json, indent=2)
            response = HttpResponse(json_data, content_type="application/json")
            response["Content-Disposition"] = "attachment; filename=user_data.json"
            return response

        if "update_email_settings" in request.POST:
            # Unchecked checkboxes just don't send POST data
            if "send_renewal_notices" in request.POST:
                send_renewal_notices = True
            else:
                send_renewal_notices = False

            editor.user.userprofile.send_renewal_notices = send_renewal_notices
            editor.user.userprofile.save()

            user = self.request.user
            # Again, process email preferences data only if the user
            # is present in the group: 'coordinators'.
            if test_func_coordinators_only(user):
                # Unchecked checkboxes doesn't send POST data
                if "send_pending_application_reminders" in request.POST:
                    send_pending_app_reminders = True
                else:
                    send_pending_app_reminders = False
                if "send_discussion_application_reminders" in request.POST:
                    send_discussion_app_reminders = True
                else:
                    send_discussion_app_reminders = False
                if "send_approved_application_reminders" in request.POST:
                    send_approved_app_reminders = True
                else:
                    send_approved_app_reminders = False
                user.userprofile.pending_app_reminders = send_pending_app_reminders
                user.userprofile.discussion_app_reminders = (
                    send_discussion_app_reminders
                )
                user.userprofile.approved_app_reminders = send_approved_app_reminders
                user.userprofile.save()

                # Although not disallowed, we'd prefer if coordinators opted
                # to receive at least one (of the 3) type of reminder emails.
                # If they choose to receive none, we post a warning message.
                if (
                    not send_pending_app_reminders
                    and not send_discussion_app_reminders
                    and not send_pending_app_reminders
                ):
                    messages.add_message(
                        request,
                        messages.WARNING,
                        # fmt: off
                        # Translators: Coordinators are shown this message when they unselect all three types of reminder email options under preferences.
                        _("You have chosen not to receive reminder emails; as a coordinator, you should receive at least one type of reminder emails, so consider changing your preferences."),
                        # fmt: on
                    )
                else:
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        # Translators: Coordinators are shown this message when they make changes to their reminder email options under preferences.
                        _("Your reminder email preferences are updated."),
                    )

        return HttpResponseRedirect(reverse_lazy("users:home"))


class UserHomeView(View):
    """
    The view for users to see their own profile data.

    Dispatches to either EditorDetailView, if the User has an attached Editor,
    or UserDetailView otherwise.

    Does not do any access limitation; EditorDetailView and UserDetailView
    are responsible for that.
    """

    editor_view = EditorDetailView
    non_editor_view = UserDetailView

    @classonlymethod
    def as_view(cls):
        def _get_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # We can't use something like django-braces LoginRequiredMixin
                # here, because as_view applies at an earlier point in the
                # process.
                return redirect_to_login(request.get_full_path())
            if hasattr(request.user, "editor"):
                kwargs.update({"pk": request.user.editor.pk})
                return_view = cls.editor_view
            else:
                kwargs.update({"pk": request.user.pk})
                return_view = cls.non_editor_view

            return return_view.as_view()(request, *args, **kwargs)

        return _get_view


class EditorUpdateView(SelfOnly, UpdateView):
    """
    Allow Editors to add the information we can't harvest from OAuth, but
    would nonetheless like to have.

    This is intended for user during the original OAuth user creation flow, but
    can also be used if we'd like to let editors change this info later.

    We handle personally identifying information through PIIUpdateView.
    """

    model = Editor
    template_name = "users/editor_update.html"
    form_class = EditorUpdateForm


class PIIUpdateView(SelfOnly, UpdateView):
    """
    Allow Editors to add the information we can't harvest from OAuth, but
    would nonetheless like to have.

    This is intended for user during the original OAuth user creation flow, but
    can also be used if we'd like to let editors change this info later.

    We handle personally identifying information through PIIUpdateView.
    """

    model = Editor
    template_name = "users/editor_update.html"
    fields = ["real_name", "country_of_residence", "occupation", "affiliation"]

    def get_object(self):
        """
        Users may only update their own information.
        """
        try:
            assert self.request.user.is_authenticated
        except AssertionError:
            messages.add_message(
                self.request,
                messages.WARNING,
                # Translators: This message is shown to users who attempt to update their personal information without being logged in.
                _("You must be logged in to do that."),
            )
            raise PermissionDenied

        return self.request.user.editor

    def get_form(self, form_class=None):
        """
        Define get_form so that we can apply crispy styling.
        """
        if form_class is None:
            form_class = self.form_class
        form = super(PIIUpdateView, self).get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(
            Submit(
                "submit",
                # Translators: This is the button users click to confirm changes to their personal information.
                _("Update"),
                css_class="twl-btn",
            )
        )

        return form

    def get_success_url(self):
        """
        Define get_success_url so that we can add a success message.
        """
        messages.add_message(
            self.request,
            messages.SUCCESS,
            # Translators: Shown to the user when they successfully modify their personal information.
            _("Your information has been updated."),
        )
        return reverse_lazy("users:home")


class EmailChangeView(SelfOnly, FormView):
    form_class = EmailChangeForm
    template_name = "users/editor_update.html"

    def get_form_kwargs(self):
        kwargs = super(EmailChangeView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        user = self.request.user

        email = self.request.POST.get("email", False)

        if email or self.request.POST.get("use_wp_email"):
            user.email = form.cleaned_data["email"]
            user.save()

            user.userprofile.use_wp_email = form.cleaned_data["use_wp_email"]
            user.userprofile.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.add_message(
                self.request,
                messages.WARNING,
                # fmt: off
                # Translators: If a user tries to save the 'email change form' without entering one and checking the 'use my Wikipedia email address' checkbox, this message is presented.
                _("Both the values cannot be blank. Either enter a email or check the box."),
                # fmt: on
            )
            return HttpResponseRedirect(reverse_lazy("users:email_change"))

    def get_object(self):
        """
        Users may only update their own email.
        """
        try:
            assert self.request.user.is_authenticated
        except AssertionError:
            messages.add_message(
                self.request,
                messages.WARNING,
                # Translators: If a user tries to do something (such as updating their email) when not logged in, this message is presented.
                _("You must be logged in to do that."),
            )
            raise PermissionDenied

        return self.request.user

    def get_success_url(self):
        if self.request.user.email:
            messages.add_message(
                self.request,
                messages.SUCCESS,
                # Translators: Shown to users when they successfully modify their email. Don't translate {email}.
                _("Your email has been changed to {email}.").format(
                    email=self.request.user.email
                ),
            )
            return _redirect_to_next_param(self.request)
        else:
            messages.add_message(
                self.request,
                messages.WARNING,
                # fmt: off
                # Translators: If the user has not filled out their email, they can browse the website but cannot apply for access to resources.
                _("Your email is blank. You can still explore the site, but you won't be able to apply for access to partner resources without an email."),
                # fmt: on
            )
            return reverse_lazy("users:home")


class RestrictDataView(SelfOnly, FormView):
    """
    Self-only view that allows users to set their data processing as
    restricted. Implemented as a separate page because this impacts their
    ability to interact with the website. We want to make sure they
    definitely mean to do this.
    """

    template_name = "users/restrict_data.html"
    form_class = RestrictDataForm

    def get_form_kwargs(self):
        kwargs = super(RestrictDataView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_object(self, queryset=None):
        try:
            assert self.request.user.is_authenticated
        except AssertionError:
            messages.add_message(
                self.request,
                messages.WARNING,
                # Translators: This message is shown to users who attempt to update their data processing without being logged in.
                _("You must be logged in to do that."),
            )
            raise PermissionDenied

        return self.request.user.userprofile

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.form_class
        form = super(RestrictDataView, self).get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(
            Submit(
                "submit",
                # Translators: This is the button users click to confirm changes to their personal information.
                _("Confirm"),
                css_class="twl-btn",
            )
        )

        return form

    def form_valid(self, form):
        coordinators = get_coordinators()
        restricted = get_restricted()
        if form.cleaned_data["restricted"]:
            self.request.user.groups.add(restricted)

            # If a coordinator requests we stop processing their data, we
            # shouldn't allow them to continue being one.
            if test_func_coordinators_only(self.request.user):
                self.request.user.groups.remove(coordinators)
        else:
            self.request.user.groups.remove(restricted)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("users:home")


class DeleteDataView(SelfOnly, DeleteView):
    model = User
    template_name = "users/user_confirm_delete.html"
    success_url = reverse_lazy("homepage")

    def get_object(self, queryset=None):
        return User.objects.get(pk=self.kwargs["pk"])

    # We want to blank applications too, not just delete the user
    # object, so we need to overwrite delete()
    def delete(self, request, *args, **kwargs):
        user = self.get_object()

        user_applications = user.editor.applications.all()
        for user_app in user_applications:
            # Blank any user data from this app
            user_app.rationale = "[deleted]"
            user_app.account_email = "[deleted]"
            user_app.comments = "[deleted]"

            user_app.save()

            # Delete the app's version history
            app_versions = Version.objects.get_for_object_reference(
                Application, user_app.pk
            )
            for app_version in app_versions:
                app_version.delete()

        # Also blank any comments left by this user, including their
        # username and email, which is duplicated in the comment object.
        for user_comment in Comment.objects.filter(user=user):
            user_comment.user_name = ""
            user_comment.user_email = ""
            user_comment.comment = "[deleted]"
            user_comment.save()

        # Expire any expiry date authorizations, but keep the object.
        for user_authorization in Authorization.objects.filter(
            user=user, date_expires__isnull=False
        ):
            user_authorization.date_expires = date.today() - timedelta(days=1)
            user_authorization.save()

        # Delete any bundle authorizations.
        bundle_auths = user.editor.get_bundle_authorization
        if bundle_auths:
            bundle_auths.delete()

        # Did the user authorize any authorizations?
        # If so, we need to retain their validity by shifting
        # the authorizer to TWL Team
        twl_team = User.objects.get(username="TWL Team")
        for authorization in Authorization.objects.filter(authorizer=user):
            authorization.authorizer = twl_team
            authorization.save()

        user.delete()

        return HttpResponseRedirect(self.success_url)

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


class TermsView(UpdateView):
    """
    For authenticated users, this is a perfectly normal UpdateView that updates
    their UserProfile with their decision on agreeing with the Terms of Use. It
    also displays those terms.

    For anonymous users, this view still displays the terms, but it does not
    generate or show the form for agreeing with the terms, because that wouldn't
    make any sense.
    """

    model = UserProfile
    template_name = "users/terms.html"
    form_class = TermsForm

    def get_object(self, queryset=None):
        """
        For authenticated users, returns their associated UserProfile instance.
        For anonymous users, returns None.
        """
        if self.request.user.is_authenticated:
            return self.request.user.userprofile
        else:
            return None

    def get_form(self, form_class=None):
        """
        For authenticated users, returns an instance of the form to be used in
        this view. For anonymous users, returns None.
        """
        if form_class is None:
            form_class = self.form_class
        kwargs = self.get_form_kwargs()

        if "instance" not in kwargs:
            return None
        else:
            if self.request.user.is_authenticated:
                return form_class(
                    self.request.user.userprofile, **self.get_form_kwargs()
                )
            else:
                return form_class(None, **self.get_form_kwargs())

    def get_form_kwargs(self):
        """
        For authenticated users, returns the keyword arguments for instantiating
        the form. For anonymous users, returns None.
        """
        kwargs = super(TermsView, self).get_form_kwargs()
        if self.request.user.is_authenticated:
            kwargs.update({"instance": self.request.user.userprofile})
        return kwargs

    def get_success_url(self):

        # Check if user is still eligible for bundle based on if they agreed to
        # the terms of use or not
        self.request.user.editor.wp_bundle_eligible = editor_bundle_eligible(
            self.request.user.editor
        )
        self.request.user.editor.save()
        self.request.user.editor.update_bundle_authorization()

        if self.get_object().terms_of_use:
            # If they agreed with the terms, awesome. Send them where they were
            # trying to go, if there's a meaningful `next` parameter in the URL;
            # if not, send them to their home page as a sensible default.
            # Also log the date they agreed.
            self.get_object().terms_of_use_date = datetime.date.today()
            self.get_object().save()

            return _redirect_to_next_param(self.request)

        else:
            # If they didn't agree, that's cool, but we should make sure they
            # know about the limits. Send them to their home page rather than
            # trying to parse the next parameter, because parsing next will
            # put them in an obnoxious redirect loop - send them to where
            # they were going, which promptly sends them back to the terms
            # page because they haven't agreed to the terms....
            # However, we will keep the terms_of_use_date as last updated date
            self.get_object().terms_of_use_date = datetime.date.today()
            self.get_object().save()

            return reverse_lazy("users:my_library")


class AuthorizedUsers(APIView):
    """
    API endpoint returning the list of users authorized to access a specific
    partner. For proxy partners, uses the list of Authorizations. For others,
    uses the full list of sent applications.
    """

    authentication_classes = (TokenAuthentication,)
    # TODO: We might want to set up more granular permissions for future APIs.
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk, version, format=None):
        try:
            partner = Partner.even_not_available.get(pk=pk)
        except Partner.DoesNotExist:
            message = "Couldn't find a partner with this ID."
            return Response(message, status=status.HTTP_404_NOT_FOUND)

        valid_partner_auths = get_valid_partner_authorizations(pk)

        # For Bundle partners, get auths for users who logged in within the last 2 weeks.
        if partner.authorization_method == partner.BUNDLE:
            valid_partner_auths = valid_partner_auths.filter(
                user__last_login__gt=timezone.now() - timedelta(weeks=2)
            )

        users = User.objects.filter(authorizations__in=valid_partner_auths).distinct()

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ListApplicationsUserView(SelfOnly, ListView):
    model = Editor
    template_name = "users/my_applications.html"

    def get_object(self):
        assert "pk" in list(self.kwargs.keys())
        try:
            return Editor.objects.get(pk=self.kwargs["pk"])
        except Editor.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(ListApplicationsUserView, self).get_context_data(**kwargs)
        editor = self.get_object()
        context["object_list"] = (
            editor.applications.model.include_invalid.filter(editor=editor)
            .exclude(partner__authorization_method=Partner.BUNDLE)
            .order_by("status", "-date_closed")
        )
        return context


class AuthorizationReturnView(SelfOnly, UpdateView):
    model = Authorization
    template_name = "users/authorization_confirm_return.html"
    fields = ["date_expires"]

    def get_object(self):
        assert "pk" in list(self.kwargs.keys())
        try:
            return Authorization.objects.get(pk=self.kwargs["pk"])
        except Authorization.DoesNotExist:
            raise Http404

    def form_valid(self, form):
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        authorization = self.get_object()
        authorization.date_expires = yesterday
        authorization.save()
        messages.add_message(
            self.request,
            messages.SUCCESS,
            # Translators: This message is shown once the access to a partner has successfully been returned.
            _("Access to {} has been returned.").format(authorization.partners.get()),
        )
        return HttpResponseRedirect(reverse("users:my_library"))


class LibraryRedirectView(RedirectView):
    permanent = True
    url = reverse_lazy("users:my_library")


class WithdrawApplication(RedirectView):
    url = "/"

    def get_redirect_url(self, *args, **kwargs):
        withdraw_id = kwargs["id"]
        application_id = kwargs["pk"]
        applications = Application.objects.filter(pk=withdraw_id)
        for application in applications:
            application.status = Application.INVALID
            application.save()
        message = f"Your application has been withdrawn successfully. Head over to <a class='twl-links' href='/users/my_applications/{application_id}'>My Applications</a> to view the status."
        messages.add_message(self.request, messages.SUCCESS, message)
        return super().get_redirect_url(*args, **kwargs)


# Cache this view for 60 minutes, vary on language and cookie
@method_decorator(cache_page(60 * 60), name="dispatch")
@method_decorator(vary_on_headers("Accept-Language", "Cookie"), name="dispatch")
# Ensure presence of CSRF Cookie
@method_decorator(ensure_csrf_cookie, name="get")
class MyLibraryView(TemplateView):
    template_name = "users/redesigned_my_library.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = (
            User.objects.prefetch_related("authorizations")
            .select_related("editor", "userprofile")
            .get(pk=self.request.user.pk)
        )
        language_code = get_language()
        partner_search_list = []

        self._build_user_collection_object(
            context, language_code, user, partner_search_list
        )
        self._build_available_collection_object(
            context, language_code, context["partner_id_set"], partner_search_list
        )

        # Store the result of `learn_cache_key` for invalidation
        user.userprofile.my_library_cache_key = learn_cache_key(
            self.request, vary_response
        )
        user.userprofile.save()

        context["user"] = user
        context["editor"] = user.editor
        context["bundle_authorization"] = Partner.BUNDLE
        context["proxy_authorization"] = Partner.PROXY
        context["searchable"] = Partner.SEARCHABLE
        context["partially_searchable"] = Partner.PARTIALLY_SEARCHABLE
        context["bundle_criteria"] = {
            # Translators: This text is shown next to a tick or cross denoting whether the current user has made more than 500 edits from their Wikimedia account.
            _("500+ edits"): user.editor.wp_enough_edits,
            # Translators: This text is shown next to a tick or cross denoting whether the current user has Wikimedia account that is at least 6 months old.
            _("6+ months editing"): user.editor.wp_account_old_enough,
            # Translators: This text is shown next to a tick or cross denoting whether the current user has made more than 10 edits within the last month (30 days) from their Wikimedia account.
            _("10+ edits in the last month"): user.editor.wp_enough_recent_edits,
            # Translators: This text is shown next to a tick or cross denoting whether the current user's Wikimedia account has been blocked on any project.
            _("No active blocks"): user.editor.wp_not_blocked,
        }

        return context

    def _build_user_collection_object(
        self, context, language_code, user, partner_search_list
    ):
        """
        Helper function to build a user collections object that will
        fill the My Collections section of the redesigned My Library
        template
        ----------
        context : dict
            The context dictionary
        language_code: str
            The language code that some tags and descriptions will be translated to
        user: User
            The User object that will serve to filter authorizations
        partner_search_list: list
            A list of all of the partners that will feed FuseJS for live search
            and filtering

        Returns
        -------
        dict
            The context dictionary with the user collections added
        """
        today = datetime.date.today()
        user_authorizations = user.authorizations.prefetch_related("partners").filter(
            Q(date_expires__gte=today) | Q(date_expires=None), user=user
        )

        expired_user_authorizations = user.authorizations.prefetch_related(
            "partners"
        ).filter(date_expires__lt=today, user=user)
        favorites = user.userprofile.favorites.all()
        favorite_ids = [f.pk for f in favorites]

        partner_id_set = set()

        context["user_collections"] = self._build_authorization_object(
            user_authorizations, language_code, partner_id_set, partner_search_list
        )
        context["expired_user_collections"] = self._build_authorization_object(
            expired_user_authorizations,
            language_code,
            partner_id_set,
            partner_search_list,
        )

        if len(favorite_ids) > 0:
            context["favorite_collections"] = self._build_authorization_object(
                user_authorizations,
                language_code,
                partner_id_set,
                partner_search_list,
                favorite_ids,
            )
            context["expired_favorite_collections"] = self._build_authorization_object(
                expired_user_authorizations,
                language_code,
                partner_id_set,
                partner_search_list,
                favorite_ids,
            )
        else:
            context["favorite_collections"] = []
            context["expired_favorite_collections"] = []

        context["favorite_ids"] = favorite_ids
        context["favorites_count"] = len(context["favorite_collections"]) + len(
            context["expired_favorite_collections"]
        )
        context["partner_id_set"] = partner_id_set
        context["number_user_collections"] = len(partner_id_set)

        return context

    def _build_authorization_object(
        self,
        authorization_queryset,
        language_code,
        partner_id_set,
        partner_search_list,
        favorite_ids=None,
    ):
        """
        Helper function to convert an Authorization queryset to an object that the
        view can parse
        ----------
        authorization_queryset : Queryset<Authorization>
            The authorization queryset
        language_code: str
            The language code that some tags and descriptions will be translated to
        partner_id_set: set
            A set that will be filled with partner IDs. These partners will be excluded
            in the Available Collections section
        partner_search_list: list
            A list of all of the partners that will feed FuseJS for live search
            and filtering
        favorite_ids: list or None
            A list of partner IDs that have been added to a user's favorites

        Returns
        -------
        list
            A list that contains the transformed Authorization queryset
        """
        user_authorization_obj = []
        favorites_obj = []

        for user_authorization in authorization_queryset:
            partner_filtered_list = PartnerFilter(
                self.request.GET,
                queryset=user_authorization.partners.prefetch_related(
                    "languages"
                ).all(),
                language_code=language_code,
            )
            # If there are no collections after filtering, we will skip this auth
            if partner_filtered_list.qs.count() == 0:
                continue
            else:

                open_app = user_authorization.get_open_app

                if user_authorization.date_expires:
                    if user_authorization.date_expires < date.today():
                        has_expired = True
                    else:
                        has_expired = False
                else:
                    has_expired = False

                for user_authorization_partner in partner_filtered_list.qs:
                    # Obtaining translated partner description
                    partner_short_description_key = "{pk}_short_description".format(
                        pk=user_authorization_partner.pk
                    )
                    partner_description_key = "{pk}_description".format(
                        pk=user_authorization_partner.pk
                    )
                    partner_descriptions = get_partner_description(
                        language_code,
                        partner_short_description_key,
                        partner_description_key,
                    )
                    (
                        partner_phabricator_tasks,
                        partner_phabricator_disabled,
                    ) = _build_task_state(user_authorization_partner.phab_task_qs)

                    try:
                        partner_logo = user_authorization_partner.logos.logo.url
                    except PartnerLogo.DoesNotExist:
                        partner_logo = None
                    # Getting tags from locale files
                    translated_tags = get_tag_names(
                        language_code, user_authorization_partner.new_tags
                    )
                    access_url = user_authorization_partner.get_access_url
                    user_auth_dict = {
                        "auth_pk": user_authorization.pk,
                        "auth_date_authorized": user_authorization.date_authorized,
                        "auth_date_expires": user_authorization.date_expires,
                        "auth_is_valid": user_authorization.is_valid,
                        "auth_latest_sent_app": user_authorization.get_latest_sent_app,
                        "auth_open_app": open_app,
                        "auth_has_expired": has_expired,
                        "partner_pk": user_authorization_partner.pk,
                        "partner_name": user_authorization_partner.company_name,
                        "partner_logo": partner_logo,
                        "partner_short_description": partner_descriptions[
                            "short_description"
                        ],
                        "partner_description": partner_descriptions["description"],
                        "partner_phabricator_tasks": partner_phabricator_tasks,
                        "partner_phabricator_disabled": partner_phabricator_disabled,
                        "partner_languages": user_authorization_partner.get_languages,
                        "partner_tags": translated_tags,
                        "partner_authorization_method": user_authorization_partner.authorization_method,
                        "partner_access_url": access_url,
                        "partner_is_not_available": user_authorization_partner.is_not_available,
                        "partner_is_waitlisted": user_authorization_partner.is_waitlisted,
                        "searchable": user_authorization_partner.searchable,
                    }

                    if partner_descriptions["description"]:
                        partner_desc = bleach.clean(
                            partner_descriptions["description"],
                            tags=[],
                            strip=True,
                        )
                    else:
                        partner_desc = None

                    if partner_descriptions["short_description"]:
                        partner_short_desc = bleach.clean(
                            partner_descriptions["short_description"],
                            tags=[],
                            strip=True,
                        )
                    else:
                        partner_short_desc = None

                    if favorite_ids:
                        if user_authorization_partner.pk in favorite_ids:
                            user_authorization_obj.append(user_auth_dict)
                            partner_id_set.add(user_authorization_partner.pk)
                            partner_search_list.append(
                                {
                                    "partner_pk": user_authorization_partner.pk,
                                    "partner_name": user_authorization_partner.company_name,
                                    "partner_short_description": partner_short_desc,
                                    "partner_description": partner_desc,
                                    "partner_phabricator_tasks": partner_phabricator_tasks,
                                    "collection_type": "FAVORITES",
                                }
                            )
                    else:
                        user_authorization_obj.append(user_auth_dict)
                        partner_id_set.add(user_authorization_partner.pk)
                        partner_search_list.append(
                            {
                                "partner_pk": user_authorization_partner.pk,
                                "partner_name": user_authorization_partner.company_name,
                                "partner_short_description": partner_short_desc,
                                "partner_description": partner_desc,
                                "partner_phabricator_tasks": partner_phabricator_tasks,
                                "collection_type": "USER",
                            }
                        )

        # Sort by partner name
        return sorted(user_authorization_obj, key=lambda k: k["partner_name"])

    def _build_available_collection_object(
        self, context, language_code, partner_id_set, partner_search_list
    ):
        """
        Helper function to build an available collections object that will
        fill the Available Collections section of the redesigned My Library
        template
        ----------
        context : dict
            The context dictionary
        language_code: str
            The language code that some tags and descriptions will be translated to
        partner_id_set: set
            A set of partner IDs which are to be excluded from the query because
            they're already in the My Collections section of the interface
        partner_search_list: list
            A list of all of the partners that will feed FuseJS for live search
            and filtering

        Returns
        -------
        dict
            The context dictionary with the available collections added
        """
        if self.request.user.is_staff:
            available_collections = (
                Partner.even_not_available.order_by("company_name")
                .exclude(authorization_method__in=[Partner.BUNDLE])
                .exclude(id__in=partner_id_set)
            )
        else:
            # Available collections do not include bundle partners and collections
            # that the user is already authorized to access
            available_collections = Partner.objects.exclude(
                authorization_method__in=[Partner.BUNDLE]
            ).exclude(id__in=partner_id_set)

        partner_filtered_list = PartnerFilter(
            self.request.GET,
            queryset=available_collections,
            language_code=language_code,
        )

        context["filter"] = partner_filtered_list

        available_collection_obj = []
        for available_collection in partner_filtered_list.qs:
            # Obtaining translated partner description
            partner_short_description_key = "{pk}_short_description".format(
                pk=available_collection.pk
            )
            partner_description_key = "{pk}_description".format(
                pk=available_collection.pk
            )
            partner_descriptions = get_partner_description(
                language_code, partner_short_description_key, partner_description_key
            )
            try:
                partner_logo = available_collection.logos.logo.url
            except PartnerLogo.DoesNotExist:
                partner_logo = None

            partner_phabricator_tasks, partner_phabricator_disabled = _build_task_state(
                available_collection.phab_task_qs
            )

            # Getting tags from locale files
            translated_tags = get_tag_names(
                language_code, available_collection.new_tags
            )
            available_collection_obj.append(
                {
                    "partner_pk": available_collection.pk,
                    "partner_name": available_collection.company_name,
                    "partner_logo": partner_logo,
                    "short_description": partner_descriptions["short_description"],
                    "description": partner_descriptions["description"],
                    "partner_phabricator_tasks": partner_phabricator_tasks,
                    "partner_phabricator_disabled": partner_phabricator_disabled,
                    "languages": available_collection.get_languages,
                    "tags": translated_tags,
                    "is_not_available": available_collection.is_not_available,
                    "is_waitlisted": available_collection.is_waitlisted,
                    "searchable": available_collection.searchable,
                }
            )

            if partner_descriptions["description"]:
                partner_desc = bleach.clean(
                    partner_descriptions["description"],
                    tags=[],
                    strip=True,
                )
            else:
                partner_desc = None

            if partner_descriptions["short_description"]:
                partner_short_desc = bleach.clean(
                    partner_descriptions["short_description"],
                    tags=[],
                    strip=True,
                )
            else:
                partner_short_desc = None

            partner_search_list.append(
                {
                    "partner_pk": available_collection.pk,
                    "partner_name": available_collection.company_name,
                    "partner_short_description": partner_short_desc,
                    "partner_description": partner_desc,
                    "collection_type": "AVAILABLE",
                }
            )

        context["available_collections"] = sorted(
            available_collection_obj, key=lambda k: k["partner_name"]
        )
        context["number_available_collections"] = len(available_collection_obj)
        context["partner_search_list"] = json.dumps(partner_search_list)

        return context


class FavoriteCollectionView(APIView):
    """
    Handles AJAX request for editors favoriting their collections
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        data = dict(request.data)
        data.update({"user_profile_pk": request.user.userprofile.pk})
        serializer = FavoriteCollectionSerializer(data=data)
        response_status = status.HTTP_400_BAD_REQUEST
        if serializer.is_valid():
            serializer.save()
            response_status = status.HTTP_200_OK
            if serializer.data.get("added"):
                response_status = status.HTTP_201_CREATED
            return Response(serializer.data, status=response_status)
        return Response(serializer.errors, status=response_status)
