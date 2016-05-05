from django.conf.urls import url

from TWLight.applications import views

urlpatterns = [
    url(r'^request/$',
        views.RequestApplicationView.as_view(),
        name='request'
    ),
    url(r'^apply/$',
        views.SubmitApplicationView.as_view(),
        name='apply'
    ),
    url(r'^evaluate/(?P<pk>\d+)/$',
        views.EvaluateApplicationView.as_view(),
        name='evaluate'
    ),
    url(r'^dashboard/$',
        views.DashboardView.as_view(),
        name='dashboard'
    ),
    url(r'^list/$',
        views.ListApplicationsView.as_view(),
        name='list'
    ),
    url(r'^list/approved/$',
        views.ListApprovedApplicationsView.as_view(),
        name='list_approved'
    ),
    url(r'^list/rejected/$',
        views.ListRejectedApplicationsView.as_view(),
        name='list_rejected'
    ),
    url(r'^list/expiring/$',
        views.ListExpiringApplicationsView.as_view(),
        name='list_expiring'
    ),
    url(r'^diff/(?P<pk>\d+)/$',
        views.DiffApplicationsView.as_view(),
        name='diff'
    ),
]
