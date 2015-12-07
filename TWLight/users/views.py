from django.views.generic.detail import DetailView
from django.contrib.auth.models import User

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
        return context
