from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.utils.decorators import classonlymethod

from TWLight.view_mixins import CoordinatorsOrSelf, SelfOnly

from .forms import EditorUpdateForm
from .models import Editor


class UserDetailView(SelfOnly, TemplateView):
    template_name = 'users/user_detail.html'

    def get_object(self):
        """
        Although 'user' is part of the default context, we need to define a
        get_object in order to be able to use the SelfOnly mixin.
        """
        assert 'pk' in self.kwargs.keys()
        return User.objects.get(pk=self.kwargs['pk'])



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
                # We can't use the django-braces LoginRequiredMixin here,
                # because as_view applies at an earlier point in the process.
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
    """
    model = Editor
    template_name = 'users/editor_update.html'
    form_class = EditorUpdateForm




class DenyAuthenticatedUsers(View):
    """
    This view is provided for use in view_mixins.py.

    The default UserPassesTestMixin redirects all users through
    settings.LOGIN_URL if they fail the test. This isn't the behavior we want;
    users who are already logged-in but don't pass the test should get
    PermissionDenied. Only unauthenticated users should be asked to log in.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            raise PermissionDenied
        else:
            return redirect_to_login(request.get_full_path())            
