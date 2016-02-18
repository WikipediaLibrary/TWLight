from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.applications import views

urlpatterns = [
    url(r'^request/', login_required(
        views.RequestForApplicationView.as_view()),
        name='request'
    ),
    url(r'^apply/(?P<pk>\d+)/', login_required(
        views.SubmitApplicationView.as_view()),
        name='apply'
    ),
]
