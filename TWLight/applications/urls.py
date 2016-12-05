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
    url(r'^apply/(?P<pk>\d+)/$',
        views.SubmitSingleApplicationView.as_view(),
        name='apply_single'
    ),
    url(r'^evaluate/(?P<pk>\d+)/$',
        views.EvaluateApplicationView.as_view(),
        name='evaluate'
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
    url(r'^list/sent/$',
        views.ListSentApplicationsView.as_view(),
        name='list_sent'
    ),
    url(r'^send/$',
        views.ListReadyApplicationsView.as_view(),
        name='send'
    ),
    url(r'^send/(?P<pk>\d+)/$',
        views.SendReadyApplicationsView.as_view(),
        name='send_partner'
    ),
    url(r'^batch_edit/$',
        views.BatchEditView.as_view(),
        name='batch_edit'
    ),
    url(r'^diff/(?P<pk>\d+)/$',
        views.DiffApplicationsView.as_view(),
        name='diff'
    ),
]
