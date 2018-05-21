from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

csv_urlpatterns = [
    url(r'^app_time_histogram/$',
        views.CSVAppTimeHistogram.as_view(),
        name='app_time_histogram'
    ),

    url(r'^app_medians/$',
        views.CSVAppMedians.as_view(),
        name='app_medians'
    ),

    url(r'^app_distribution/$',
        views.CSVAppDistribution.as_view(),
        name='app_distribution'
    ),

    url(r'^app_distribution/(?P<pk>\d+)/$',
        views.CSVAppDistribution.as_view(),
        name='app_distribution_by_partner'
    ),

    url(r'^app_count/(?P<pk>\d+)/$',
        views.CSVAppCountByPartner.as_view(),
        name='app_count_by_partner'
    ),

    url(r'^app_count/approved/(?P<pk>\d+)/$',
        views.CSVAppCountByPartner.as_view(),
        kwargs={'approved_or_sent': True},
        name='approved_or_sent_app_count_by_partner'
    ),

    url(r'^user_count/(?P<pk>\d+)/$',
        views.CSVUserCountByPartner.as_view(),
        name='user_count_by_partner'
    ),

    url(r'^page_views/$',
        login_required(views.CSVPageViews.as_view()),
        name='page_views'
    ),

    url(r'^page_views/(?P<path>[a-zA-Z0-9_\-/]+)/$',
        views.CSVPageViewsByPath.as_view(),
        name='page_views_by_path'
    ),
    
    url(r'^num_applications/$',
        views.CSVNumApprovedApplications.as_view(),
        name='num_applications'
    ),

    url(r'^user_language/$',
        views.CSVUserLanguage.as_view(),
        name='user_language'
    ),
]
