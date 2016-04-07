from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django.contrib.auth.models import User
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from django.utils.translation import ugettext as _

from .models import Editor


class EditorDetailView(DetailView):
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
        context['editor'] = self.get_object().editor
        context['object_list'] = self.get_object().applications.all().order_by('status')
        return context


class EditorUpdateView(UpdateView):
    """
    Allow Editors to add the information we can't harvest from OAuth, but
    would nonetheless like to have.

    This is intended for user during the original OAuth user creation flow, but
    can also be used if we'd like to let editors change this info later.
    """
    model = Editor
    fields = ['home_wiki', 'contributions']
    template_name = 'users/editor_update.html'

    def get_form(self, form_class):
        form = super(EditorUpdateView, self).get_form(form_class)

        form.helper = FormHelper()
        form.helper.add_input(Submit(
            'submit',
            _('Update profile'),
            css_class='center-block'))

        return form
