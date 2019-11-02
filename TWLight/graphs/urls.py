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
