from django.urls import re_path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    re_path(
        r"^u/(?P<url>http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)$",
        login_required(views.EZProxyAuth.as_view()),
        name="ezproxy_auth_u",
    ),
    re_path(
        r"^r/(?P<token>ezp\.([a-zA-Z]|[0-9]|[$-_@.&+])+)$",
        login_required(views.EZProxyAuth.as_view()),
        name="ezproxy_auth_r",
    ),
]
