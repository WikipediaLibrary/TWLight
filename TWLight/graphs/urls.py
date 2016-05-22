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
]
