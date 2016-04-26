from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from TWLight.applications import views

urlpatterns = [
    url(r'^request/$', login_required(
        views.RequestApplicationView.as_view()),
        name='request'
    ),
    url(r'^apply/$', login_required(
        views.SubmitApplicationView.as_view()),
        name='apply'
    ),
    url(r'^evaluate/(?P<pk>\d+)/$', login_required(
        views.EvaluateApplicationView.as_view()),
        name='evaluate'
    ),
    url(r'^list/$', login_required(
        views.ListApplicationsView.as_view()),
        name='list'
    ),
    url(r'^list/approved/$', login_required(
        views.ListApprovedApplicationsView.as_view()),
        name='list_approved'
    ),
    url(r'^list/rejected/$', login_required(
        views.ListRejectedApplicationsView.as_view()),
        name='list_rejected'
    ),
    url(r'^list/expiring/$', login_required(
        views.ListExpiringApplicationsView.as_view()),
        name='list_expiring'
    ),
    url(r'^diff/(?P<pk>\d+)/$', login_required(
        views.DiffApplicationsView.as_view()),
        name='diff'
    ),
]
