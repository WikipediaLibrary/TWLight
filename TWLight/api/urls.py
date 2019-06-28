from django.conf.urls import url

from TWLight.users import views

urlpatterns = [
    url(r'^(?P<version>(v1))/users/authorizations/partner/(?P<pk>\d+)/$',
        views.AuthorizedUsers.as_view())
    ]
