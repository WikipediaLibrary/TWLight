from django.conf.urls import url

from . import views

csv_urlpatterns = [
    url(r'^num_partners/$',
        views.CSVNumPartners.as_view(),
        name='num_partners'
    ),

    url(r'^home_wiki_pie/$',
        views.CSVHomeWikiPie.as_view(),
        name='home_wiki_pie'
    ),

    url(r'^home_wiki_over_time/$',
        views.CSVHomeWikiOverTime.as_view(),
        name='home_wiki_over_time'
    ),

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
        kwargs={'approved': True},
        name='approved_app_count_by_partner'
    ),

    url(r'^user_count/(?P<pk>\d+)/$',
        views.CSVUserCountByPartner.as_view(),
        name='user_count_by_partner'
    ),

    url(r'^page_views/$',
        views.CSVPageViews.as_view(),
        name='page_views'
    ),

    url(r'^page_views/(?P<path>[a-zA-Z0-9_\-/]+)/$',
        views.CSVPageViewsByPath.as_view(),
        name='page_views_by_path'
    ),
]
