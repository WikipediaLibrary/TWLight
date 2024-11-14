from django.urls import re_path

from TWLight.users import views

urlpatterns = [
    re_path(
        r"^(?P<version>(v0))/users/authorizations/partner/(?P<pk>\d+)/$",
        views.AuthorizedUsers.as_view(),
    ),
    re_path(
        r"^(?P<version>(v0))/users/eligibility/(?P<wp_username>[\w\s\S]+)/$",
        views.UserEligibility.as_view(),
    ),
]
