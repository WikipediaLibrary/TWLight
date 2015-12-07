from django.views.generic.detail import DetailView

from TWLight.users.models import Editor

class EditorDetailView(DetailView):
	model = Editor
