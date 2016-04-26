from django.contrib.auth.models import User
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.utils.decorators import classonlymethod

from TWLight.view_mixins import CoordinatorsOrSelf, SelfOnly

from .forms import EditorUpdateForm
from .models import Editor


class UserDetailView(TemplateView):
    template_name = 'users/user_detail.html'

    # Remember that 'user' is part of the default context.



class EditorDetailView(CoordinatorsOrSelf, DetailView):
    """
    User profile data page.

    This uses User as the base model so that the pk indicated in the URL
    will be the same as the pk used in the admin site to access a given
    user. However, the data presented is all profile data from the Editor
    model, which is what site users need to actually make decisions about
    access grants.
    """
    model = User
    template_name = 'users/editor_detail.html'

    def get_context_data(self, **kwargs):
        context = super(EditorDetailView, self).get_context_data(**kwargs)
        editor = self.get_object().editor
        context['editor'] = editor
        context['object_list'] = self.get_object().applications.all().order_by('status')
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
            if hasattr(request.user, 'editor'):
                return_view = cls.editor_view
            else:
                return_view = cls.non_editor_view

            print return_view.as_view()

            if 'pk' in kwargs:
                return return_view.as_view()(request, *args, **kwargs)
            else:
                kwargs.update({'pk': request.user.pk})
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
