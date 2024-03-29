from django.urls import re_path, path

from . import views

urlpatterns = [
    path(
        r"",
        views.PartnersFilterView.as_view(),
        name="filter",
    ),
    re_path(r"^(?P<pk>\d+)/$", views.PartnersDetailView.as_view(), name="detail"),
    re_path(
        r"^toggle_waitlist/(?P<pk>\d+)/$",
        views.PartnersToggleWaitlistView.as_view(),
        name="toggle_waitlist",
    ),
    re_path(r"^(?P<pk>\d+)/users/$", views.PartnerUsers.as_view(), name="users"),
]
