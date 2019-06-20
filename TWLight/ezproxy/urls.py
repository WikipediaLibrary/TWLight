from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    url(r'^auth$',
        login_required(views.EZProxyAuth.as_view()),
        name='ezproxy_auth'
    ),
]