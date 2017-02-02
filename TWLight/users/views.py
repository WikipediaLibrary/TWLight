from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, resolve, Resolver404
from django.http import Http404
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.utils.decorators import classonlymethod
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from TWLight.view_mixins import CoordinatorsOrSelf, SelfOnly, coordinators

from .forms import EditorUpdateForm, SetLanguageForm, TermsForm
from .models import Editor, UserProfile


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
        context['language_form'] = SetLanguageForm()
        context['password_form'] = PasswordChangeForm(user=self.request.user)
        return context



class EditorDetailView(CoordinatorsOrSelf, DetailView):
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
        context['object_list'] = editor.applications.all().order_by('status')
        context['form'] = EditorUpdateForm(instance=editor)
        context['language_form'] = SetLanguageForm()

        try:
            if self.request.user.editor == editor and not editor.contributions:
                messages.add_message(self.request, messages.WARNING,
                    _('Please update your contributions to Wikipedia (below) to '
                      'help coordinators evaluate your applications.'))
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
            raise PermissionDenied

        return self.request.user.editor


    def get_form(self, form_class):
        """
        Define get_form so that we can apply crispy styling.
        """
        form = super(PIIUpdateView, self).get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit(
            'submit',
            _('Update information'),
            css_class='center-block'))

        return form


    def get_success_url(self):
        """
        Define get_success_url so that we can add a success message.
        """
        messages.add_message(self.request, messages.SUCCESS,
            _('Your information has been updated.'))
        return reverse_lazy('users:home')



class EmailChangeView(SelfOnly, UpdateView):
    model = User
    template_name = 'users/editor_update.html'
    fields = ['email']

    def get_object(self):
        """
        Users may only update their own email.
        """
        try:
            assert self.request.user.is_authenticated()
        except AssertionError:
            raise PermissionDenied

        return self.request.user


    def get_form(self, form_class):
        """
        Define get_form so that we can apply crispy styling.
        """
        form = super(EmailChangeView, self).get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit(
            'submit',
            _('Update email'),
            css_class='center-block'))

        return form


    def get_success_url(self):
        """
        Define get_success_url so that we can add a success message.
        """
        messages.add_message(self.request, messages.SUCCESS,
            _('Your email has been changed to {email}.').format(
                email=self.request.user.email))
        return reverse_lazy('users:home')




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


    def get_form(self, form_class):
        """
        For authenticated users, returns an instance of the form to be used in
        this view. For anonymous users, returns None.
        """
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
        def is_real_url(url):
            """
            Users might have altered the URL parameters. Let's not just blindly
            redirect; let's actually make sure we can get somewhere first.
            """
            try:
                resolve(url)
                return True
            except Resolver404:
                return False


        if self.get_object().terms_of_use:
            # If they agreed with the terms, awesome. Send them where they were
            # trying to go, if there's a meaningful `next` parameter in the URL;
            # if not, send them to their home page as a sensible default.
            next_param = self.request.GET.get(REDIRECT_FIELD_NAME, '')
            if (next_param and
                is_safe_url(url=next_param, host=self.request.get_host()) and
                is_real_url(next_param)):
                return next_param
            else:
                return reverse_lazy('users:home')

        else:
            # If they didn't agree, that's cool, but we should make sure they
            # know about the limits. Send them to their home page rather than
            # trying to parse the next parameter, because parsing next will
            # put them in an obnoxious redirect loop - send them to where
            # they were going, which promptly sends them back to the terms
            # page because they haven't agreed to the terms....
            if self.request.user in coordinators.user_set.all():
                fail_msg = _('You may explore the site, but you will not be '
                  'able to apply for access to materials or evaluate '
                  'applications unless you agree with the terms of use.')
            else:
                fail_msg = _('You may explore the site, but you will not be '
                  'able to apply for access to materials unless you agree with '
                  'the terms of use.')

            messages.add_message(self.request, messages.WARNING, fail_msg)
            return reverse_lazy('users:home')
