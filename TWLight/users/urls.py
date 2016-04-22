from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.users import views

urlpatterns = [
    url(r'^$', 
        login_required(views.UserHomeView.as_view()),
        name='home'),
    url(r'^(?P<pk>\d+)/$',
        login_required(views.EditorDetailView.as_view()),
        name='editor_detail'),
    url(r'^update/(?P<pk>\d+)/$',
        login_required(views.EditorUpdateView.as_view()),
        name='editor_update'),
]
