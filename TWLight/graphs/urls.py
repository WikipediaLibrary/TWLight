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
]
