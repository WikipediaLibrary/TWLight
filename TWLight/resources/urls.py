from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', 
        views.PartnersListView.as_view(),
        name='list'
    ),
    url(r'^(?P<pk>\d+)/$',
        views.PartnersDetailView.as_view(),
        name='detail'
    ),
]
