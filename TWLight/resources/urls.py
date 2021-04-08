from django.conf.urls import url
from .filters import PartnerFilter

from . import views

urlpatterns = [
    url(
        r"^$",
        views.PartnersFilterView.as_view(),
        name="filter",
    ),
    url(r"^(?P<pk>\d+)/$", views.PartnersDetailView.as_view(), name="detail"),
    url(
        r"^toggle_waitlist/(?P<pk>\d+)/$",
        views.PartnersToggleWaitlistView.as_view(),
        name="toggle_waitlist",
    ),
    url(r"^(?P<pk>\d+)/users/$", views.PartnerUsers.as_view(), name="users"),
]
