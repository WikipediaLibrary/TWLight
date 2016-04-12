"""
TWLight URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
"""

from django.conf.urls import include, url
from django.contrib import admin

from TWLight.users import authorization as auth
from TWLight.users.urls import urlpatterns as users_urls
from TWLight.applications.urls import urlpatterns as applications_urls


urlpatterns = [
	# Built-in
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^accounts/', include('allauth.urls')),
    url(r'^comments/', include('django.contrib.comments.urls')),

    url(r'^oauth/login/$',
        auth.OAuthInitializeView.as_view(),
        name='oauth_login'),
    url(r'^oauth/callback/$',
        auth.OAuthCallbackView.as_view(),
        name='oauth_callback'),

    # TWLight apps
    url(r'^users/', include(users_urls, namespace="users")),
    url(r'^applications/', include(applications_urls,namespace="applications")),
]
