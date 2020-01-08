from datetime import date, timedelta
import json

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django.db.models import Q
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, resolve, Resolver404, reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, FormView, DeleteView
from django.views.generic.list import ListView
from django.utils.decorators import classonlymethod
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django_comments.models import Comment

from TWLight.resources.models import Partner
from TWLight.view_mixins import CoordinatorOrSelf, SelfOnly, coordinators
from TWLight.users.groups import get_coordinators, get_restricted

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
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
from .models import Editor, UserProfile, Authorization
from .serializers import UserSerializer
from TWLight.applications.models import Application

import datetime

coordinators = get_coordinators()
restricted = get_restricted()

import logging

logger = logging.getLogger(__name__)


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


def _redirect_to_next_param(request):
    next_param = request.GET.get(REDIRECT_FIELD_NAME, "")
    if (
        next_param
        and is_safe_url(url=next_param, host=request.get_host())
        and _is_real_url(next_param)
    ):
        return next_param
    else:
        return reverse_lazy("users:home")


class UserDetailView(SelfOnly, TemplateView):
    template_name = "users/user_detail.html"

    def get_object(self):
        """
        Although 'user' is part of the default context, we need to define a
        get_object in order to be able to use the SelfOnly mixin.
        """
        assert "pk" in list(self.kwargs.keys())
        try:
            return User.objects.get(pk=self.kwargs["pk"])
        except User.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context["language_form"] = SetLanguageForm(user=self.request.user)
        context["password_form"] = PasswordChangeForm(user=self.request.user)
        return context


class EditorDetailView(CoordinatorOrSelf, DetailView):
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
        editor = self.get_object()
        user = self.request.user
        context["editor"] = editor  # allow for more semantic templates
        context["form"] = EditorUpdateForm(instance=editor)
        context["language_form"] = SetLanguageForm(user=user)
        context["email_form"] = UserEmailForm(user=user)
        # Check if the user is in the group: 'coordinators',
        # and add the reminder email preferences form.
        if coordinators in user.groups.all():
            context["coordinator_email_form"] = CoordinatorEmailForm(user=user)

        try:
            if user.editor == editor and not editor.contributions:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    # Translators: This message is shown on user's own profile page, encouraging them to make sure their information is up to date, so that account coordinators can use the information to judge applications.
                    _(
                        'Please <a href="{url}">update your contributions</a> '
                        "to Wikipedia to help coordinators evaluate your "
                        "applications.".format(
                            url=reverse_lazy(
                                "users:editor_update", kwargs={"pk": editor.pk}
                            )
                        )
                    ),
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
            if coordinators in user.groups.all():
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
                        # Translators: Coordinators are shown this message when they unselect all three types of reminder email options under preferences.
                        _(
                            "You have chosen not to receive reminder emails. "
                            "As a coordinator, you should receive at least one "
                            "type of reminder emails, consider changing your preferences."
                        ),
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
            if request.user.is_anonymous():
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
            assert self.request.user.is_authenticated()
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
                css_class="center-block",
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
                # Translators: If a user tries to save the 'email change form' without entering one and checking the 'use my Wikipedia email address' checkbox, this message is presented.
                _(
                    "Both the values cannot be blank. Either enter a email or check the box."
                ),
            )
            return HttpResponseRedirect(reverse_lazy("users:email_change"))

    def get_object(self):
        """
        Users may only update their own email.
        """
        try:
            assert self.request.user.is_authenticated()
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
                # Translators: If the user has not filled out their email, they can browse the website but cannot apply for access to resources.
                _(
                    "Your email is blank. You can still explore the site, "
                    "but you won't be able to apply for access to partner "
                    "resources without an email."
                ),
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
            assert self.request.user.is_authenticated()
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
                css_class="center-block",
            )
        )

        return form

    def form_valid(self, form):
        if form.cleaned_data["restricted"]:
            self.request.user.groups.add(restricted)

            # If a coordinator requests we stop processing their data, we
            # shouldn't allow them to continue being one.
            if coordinators in self.request.user.groups.all():
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
        if self.request.user.is_authenticated():
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
            return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """
        For authenticated users, returns the keyword arguments for instantiating
        the form. For anonymous users, returns None.
        """
        kwargs = super(TermsView, self).get_form_kwargs()
        if self.request.user.is_authenticated():
            kwargs.update({"instance": self.request.user.userprofile})
        return kwargs

    def get_success_url(self):

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
            # Also clear the ToU date field in case a user un-agrees
            self.get_object().terms_of_use_date = None
            self.get_object().save()

            if self.request.user in coordinators.user_set.all():
                # Translators: This message is shown if the user (who is also a coordinator) does not accept to the Terms of Use when signing up. They can browse the website but cannot apply for or evaluate applications for access to resources.
                fail_msg = _(
                    "You may explore the site, but you will not be "
                    "able to apply for access to materials or evaluate "
                    "applications unless you agree with the terms of use."
                )
            else:
                # Translators: This message is shown if the user does not accept to the Terms of Use when signing up. They can browse the website but cannot apply for access to resources.
                fail_msg = _(
                    "You may explore the site, but you will not be "
                    "able to apply for access unless you agree with "
                    "the terms of use."
                )

            messages.add_message(self.request, messages.WARNING, fail_msg)
            return reverse_lazy("users:home")


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

        if partner.authorization_method == Partner.PROXY:
            users = User.objects.filter(
                authorizations__partner=partner,
                authorizations__date_expires__gte=date.today(),
            ).distinct()
        else:
            users = User.objects.filter(
                editor__applications__status=Application.SENT,
                editor__applications__partner=partner,
            ).distinct()

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class CollectionUserView(SelfOnly, ListView):
    model = Editor
    template_name = "users/my_collection.html"

    def get_object(self):
        assert "pk" in list(self.kwargs.keys())
        try:
            return Editor.objects.get(pk=self.kwargs["pk"])
        except Editor.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(CollectionUserView, self).get_context_data(**kwargs)
        editor = self.get_object()
        today = datetime.date.today()
        proxy_bundle_authorizations = Authorization.objects.filter(
            Q(date_expires__gte=today) | Q(date_expires=None),
            user=editor.user,
            partner__authorization_method__in=[Partner.PROXY, Partner.BUNDLE],
        ).order_by("partner")
        proxy_bundle_authorizations_expired = Authorization.objects.filter(
            user=editor.user,
            date_expires__lt=today,
            partner__authorization_method__in=[Partner.PROXY, Partner.BUNDLE],
        ).order_by("partner")
        manual_authorizations = Authorization.objects.filter(
            Q(date_expires__gte=today) | Q(date_expires=None),
            user=editor.user,
            partner__authorization_method__in=[
                Partner.EMAIL,
                Partner.CODES,
                Partner.LINK,
            ],
        ).order_by("partner")
        manual_authorizations_expired = Authorization.objects.filter(
            user=editor.user,
            date_expires__lt=today,
            partner__authorization_method__in=[
                Partner.EMAIL,
                Partner.CODES,
                Partner.LINK,
            ],
        ).order_by("partner")

        for authorization_list in [
            manual_authorizations,
            proxy_bundle_authorizations,
            manual_authorizations_expired,
            proxy_bundle_authorizations_expired,
        ]:
            for each_authorization in authorization_list:
                if (
                    each_authorization.about_to_expire
                    or not each_authorization.is_valid
                ):
                    each_authorization.latest_app = each_authorization.get_latest_app()
                    if each_authorization.latest_app:
                        if not each_authorization.latest_app.is_renewable:
                            try:
                                each_authorization.open_app = Application.objects.filter(
                                    editor=editor,
                                    status__in=(
                                        Application.PENDING,
                                        Application.QUESTION,
                                        Application.APPROVED,
                                    ),
                                    partner=each_authorization.partner,
                                ).latest(
                                    "date_created"
                                )
                            except Application.DoesNotExist:
                                each_authorization.open_app = None

        context["proxy_bundle_authorizations"] = proxy_bundle_authorizations
        context[
            "proxy_bundle_authorizations_expired"
        ] = proxy_bundle_authorizations_expired
        context["manual_authorizations"] = manual_authorizations
        context["manual_authorizations_expired"] = manual_authorizations_expired
        return context


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
        context["object_list"] = editor.applications.model.include_invalid.filter(
            editor=editor
        ).order_by("status", "-date_closed")
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
        # Translators: This message is shown once the access to a partner has successfully been returned.
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Access to {} has been returned.").format(authorization.partner),
        )
        return HttpResponseRedirect(
            reverse("users:my_collection", kwargs={"pk": self.request.user.editor.pk})
        )
