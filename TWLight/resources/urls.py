from django.conf.urls import url
from django_filters.views import FilterView
from .models import Partner
from .filters import PartnerFilter

from . import views

urlpatterns = [
    url(r'^$',
        views.PartnersFilterView.as_view(filterset_class=PartnerFilter),
        name='filter'
    ),
    url(r'^(?P<pk>\d+)/$',
        views.PartnersDetailView.as_view(),
        name='detail'
    ),
    url(r'^toggle_waitlist/(?P<pk>\d+)/$',
        views.PartnersToggleWaitlistView.as_view(),
        name='toggle_waitlist'
    ),
    url(r'^(?P<pk>\d+)/users/$',
        views.PartnerUsers.as_view(),
        name='users'
    ),
    url(r'^code/(?P<pk>\d+)/$',
        views.PartnerUnassignCode.as_view(),
        name='unassign_code'
    ),
]
