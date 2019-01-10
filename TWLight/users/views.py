import json

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, resolve, Resolver404
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, FormView, DeleteView
from django.utils.decorators import classonlymethod
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _
from django_comments.models import Comment

from TWLight.view_mixins import CoordinatorOrSelf, SelfOnly, coordinators
from TWLight.users.groups import get_coordinators, get_restricted

from reversion.models import Version

from .forms import EditorUpdateForm, SetLanguageForm, TermsForm, EmailChangeForm, RestrictDataForm
from .models import Editor, UserProfile
from TWLight.applications.models import Application
from TWLight.users.models import Contact
from TWLight.users.forms import ContactUsForm

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
    next_param = request.GET.get(REDIRECT_FIELD_NAME, '')
    if (next_param and
        is_safe_url(url=next_param, host=request.get_host()) and
        _is_real_url(next_param)):
        return next_param
    else:
        return reverse_lazy('users:home')


class UserDetailView(SelfOnly, TemplateView):
    template_name = 'users/user_detail.html'

    def get_object(self):
        """
        Although 'user' is part of the default context, we need to define a
        get_object in order to be able to use the SelfOnly mixin.
        """
        assert 'pk' in self.kwargs.keys()
        try:
            return User.objects.get(pk=self.kwargs['pk'])
        except User.DoesNotExist:
            raise Http404


    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['language_form'] = SetLanguageForm(user=self.request.user)
        context['password_form'] = PasswordChangeForm(user=self.request.user)
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
    template_name = 'users/editor_detail.html'

    def get_context_data(self, **kwargs):
        context = super(EditorDetailView, self).get_context_data(**kwargs)
        editor = self.get_object()
        context['editor'] = editor # allow for more semantic templates
        context['object_list'] = editor.applications.model.include_invalid.filter(editor=editor).order_by('status', '-date_closed')
        context['form'] = EditorUpdateForm(instance=editor)
        context['language_form'] = SetLanguageForm(user=self.request.user)

        try:
            if self.request.user.editor == editor and not editor.contributions:
                messages.add_message(self.request, messages.WARNING,
                    # Translators: This message is shown on user's own profile page, encouraging them to make sure their information is up to date, so that account coordinators can use the information to judge applications.
                    _('Please <a href="{url}">update your contributions</a> '
                      'to Wikipedia to help coordinators evaluate your '
                      'applications.'.format(
                        url=reverse_lazy('users:editor_update',
                            kwargs={'pk': editor.pk}))))
        except Editor.DoesNotExist:
            """
            If the user viewing the site does not have an attached editor
            (which can happen for administrative users), this error will be
            thrown, preventing the user from viewing the site. We don't actually
            want to have a 500 in this case, though; we just want to not add the
            message, and move on.
            """
            pass

        context['password_form'] = PasswordChangeForm(user=self.request.user)

        return context

    def post(self, request, *args, **kwargs):
        editor = self.get_object()
        if "download" in request.POST:
            # When users click the Download button in the Data section of
            # their user page, provide a json with any personal information
            # they submitted to the site.

            user_json = {}
            editor_data = Editor.objects.get(pk=editor.pk)

            user_json['user_data'] = {}
            user_field_list = ['wp_username', 'contributions', 'real_name',
                'country_of_residence', 'occupation', 'affiliation']
            for field in user_field_list:
                field_data = getattr(editor_data, field)
                if field_data:
                    user_json['user_data'][field] = field_data

            user_apps = Application.objects.filter(editor=editor)
            user_json['applications'] = {}
            for app in user_apps:
                user_json['applications'][app.id] = {}
                for field in ['rationale', 'comments', 'account_email']:
                    field_data = getattr(app, field)
                    if field_data:
                        user_json['applications'][app.id][field] = field_data

            user_comments = Comment.objects.filter(user_id=editor.user.id)
            user_json['comments'] = []
            for comment in user_comments:
                user_json['comments'].append(comment.comment)

            json_data = json.dumps(user_json, indent=2)
            response = HttpResponse(json_data, content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename=user_data.json'
            return response

        return HttpResponseRedirect(reverse_lazy('users:home'))



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
            if hasattr(request.user, 'editor'):
                kwargs.update({'pk': request.user.editor.pk})
                return_view = cls.editor_view
            else:
                kwargs.update({'pk': request.user.pk})
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
    template_name = 'users/editor_update.html'
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
    template_name = 'users/editor_update.html'
    fields = ['real_name', 'country_of_residence', 'occupation', 'affiliation']

    def get_object(self):
        """
        Users may only update their own information.
        """
        try:
            assert self.request.user.is_authenticated()
        except AssertionError:
            messages.add_message (request, messages.WARNING,
                # Translators: This message is shown to users who attempt to update their personal information without being logged in.
                _('You must be logged in to do that.'))
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
        form.helper.add_input(Submit(
            'submit',
            # Translators: This is the button users click to confirm changes to their personal information.
            _('Update'),
            css_class='center-block'))

        return form


    def get_success_url(self):
        """
        Define get_success_url so that we can add a success message.
        """
        messages.add_message(self.request, messages.SUCCESS,
            # Translators: Shown to the user when they successfully modify their personal information.
            _('Your information has been updated.'))
        return reverse_lazy('users:home')



class EmailChangeView(SelfOnly, FormView):
    form_class = EmailChangeForm
    template_name = 'users/editor_update.html'

    def get_form_kwargs(self):
        kwargs = super(EmailChangeView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs


    def form_valid(self, form):
        user = self.request.user
        
        email = self.request.POST.get('email', False)
        
        if email or self.request.POST.get('use_wp_email'):
            user.email = form.cleaned_data['email']
            user.save()
                
            user.userprofile.use_wp_email = form.cleaned_data['use_wp_email']
            user.userprofile.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.add_message(self.request, messages.WARNING,
                # Translators: If a user tries to save the 'email change form' without entering one and checking the 'use my Wikipedia email address' checkbox, this message is presented.
                _('Both the values cannot be blank. Either enter a email or check the box.'))
            return HttpResponseRedirect(reverse_lazy('users:email_change'))


    def get_object(self):
        """
        Users may only update their own email.
        """
        try:
            assert self.request.user.is_authenticated()
        except AssertionError:
            messages.add_message (request, messages.WARNING,
                # Translators: If a user tries to do something (such as updating their email) when not logged in, this message is presented.
                _('You must be logged in to do that.'))
            raise PermissionDenied

        return self.request.user


    def get_success_url(self):
        if self.request.user.email:
            messages.add_message(self.request, messages.SUCCESS,
                # Translators: Shown to users when they successfully modify their email. Don't translate {email}.
                _('Your email has been changed to {email}.').format(
                    email=self.request.user.email))
            return _redirect_to_next_param(self.request)
        else:
            messages.add_message(self.request, messages.WARNING,
                # Translators: If the user has not filled out their email, they can browse the website but cannot apply for access to resources.
                _('Your email is blank. You can still explore the site, '
                  "but you won't be able to apply for access to partner "
                  'resources without an email.'))
            return reverse_lazy('users:home')



class RestrictDataView(SelfOnly, FormView):
    """
    Self-only view that allows users to set their data processing as
    restricted. Implemented as a separate page because this impacts their
    ability to interact with the website. We want to make sure they
    definitely mean to do this.
    """
    template_name = 'users/restrict_data.html'
    form_class = RestrictDataForm

    def get_form_kwargs(self):
        kwargs = super(RestrictDataView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_object(self, queryset=None):
        try:
            assert self.request.user.is_authenticated()
        except AssertionError:
            messages.add_message (request, messages.WARNING,
                # Translators: This message is shown to users who attempt to update their data processing without being logged in.
                _('You must be logged in to do that.'))
            raise PermissionDenied

        return self.request.user.userprofile


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.form_class
        form = super(RestrictDataView, self).get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit(
            'submit',
            # Translators: This is the button users click to confirm changes to their personal information.
            _('Confirm'),
            css_class='center-block'))

        return form

    def form_valid(self, form):
        if form.cleaned_data['restricted']:
            self.request.user.groups.add(restricted)

            # If a coordinator requests we stop processing their data, we
            # shouldn't allow them to continue being one.
            if coordinators in self.request.user.groups.all():
                self.request.user.groups.remove(coordinators)
        else:
            self.request.user.groups.remove(restricted)

        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy('users:home')



class DeleteDataView(SelfOnly, DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('homepage')

    def get_object(self, queryset=None):
        return User.objects.get(pk=self.kwargs['pk'])

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
                Application, user_app.pk)
            for app_version in app_versions:
                app_version.delete()

        # Also blank any comments left by this user, including their
        # username and email, which is duplicated in the comment object.
        for user_comment in Comment.objects.filter(user=user):
            user_comment.user_name = ""
            user_comment.user_email = ""
            user_comment.comment = "[deleted]"
            user_comment.save()

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
    template_name = 'users/terms.html'
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

        if 'instance' not in kwargs:
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
            kwargs.update({'instance': self.request.user.userprofile})
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
                fail_msg = _('You may explore the site, but you will not be '
                  'able to apply for access to materials or evaluate '
                  'applications unless you agree with the terms of use.')
            else:
                # Translators: This message is shown if the user does not accept to the Terms of Use when signing up. They can browse the website but cannot apply for access to resources.
                fail_msg = _('You may explore the site, but you will not be '
                  'able to apply for access unless you agree with '
                  'the terms of use.')

            messages.add_message(self.request, messages.WARNING, fail_msg)
            return reverse_lazy('users:home')



class ContactUsView(FormView):
    model=Contact
    template_name = 'users/contact.html'
    form_class = ContactUsForm
    success_url = reverse_lazy('contact')
