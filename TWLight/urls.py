"""
TWLight URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
"""

from django.conf.urls import include, url
from django.contrib import admin

from TWLight.users.urls import urlpatterns as users_urls
from TWLight.applications.urls import urlpatterns as applications_urls


urlpatterns = [
	# Built-in
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('allauth.urls')),

    # TWLight apps
    url(r'^users/', include(users_urls, namespace="users")),
    url(r'^applications/', include(applications_urls,namespace="applications")),
]
