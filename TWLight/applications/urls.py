from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.applications import views

urlpatterns = [
    url(r'^request/', login_required(
        views.RequestApplicationView.as_view()),
        name='request'
    ),
    url(r'^apply/', login_required(
        views.SubmitApplicationView.as_view()),
        name='apply'
    ),
    url(r'^evaluate/(?P<pk>\d+)/', login_required(
        views.EvaluateApplicationView.as_view()),
        name='evaluate'
    ),
    url(r'^list/', login_required(
        views.ListApplicationsView.as_view()),
        name='list'
    ),
]
