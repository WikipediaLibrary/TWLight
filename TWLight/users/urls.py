from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.users import views

urlpatterns = [
    url(r'^(?P<pk>\d+)/',
        login_required(views.EditorDetailView.as_view()),
        name='editor_detail'),
]
