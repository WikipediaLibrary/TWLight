from django.urls import re_path

from TWLight.users import views

urlpatterns = [
    re_path(
        r"^(?P<version>(v0))/users/authorizations/partner/(?P<pk>\d+)/$",
        views.AuthorizedUsers.as_view(),
    )
]
