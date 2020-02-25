"""
TWLight URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls import include, static, url
from django.contrib import admin
from django.contrib.admindocs import urls as admindocs
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_page
import django


import TWLight.i18n.views
import TWLight.i18n.urls
from TWLight.api.urls import urlpatterns as api_urls
from TWLight.applications.urls import urlpatterns as applications_urls
from TWLight.emails.views import ContactUsView
from TWLight.graphs.urls import csv_urlpatterns as csv_urls
from TWLight.graphs.views import DashboardView
from TWLight.resources.urls import urlpatterns as partners_urls
from TWLight.resources.views import (
    PartnerSuggestionView,
    SuggestionDeleteView,
    SuggestionUpvoteView,
)
from TWLight.users import authorization as auth
from TWLight.users.urls import urlpatterns as users_urls
from TWLight.users.views import TermsView
from TWLight.ezproxy.urls import urlpatterns as ezproxy_urls

from .views import LanguageWhiteListView, HomePageView, ActivityView


urlpatterns = [
    # Built-in -----------------------------------------------------------------
    url(r"^admin/doc", include(admindocs)),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^accounts/login/", auth_views.login, name="auth_login"),
    url(
        r"^accounts/logout/", auth_views.logout, {"next_page": "/"}, name="auth_logout"
    ),
    url(
        r"^password/change/$",
        auth_views.password_change,
        {"post_change_redirect": "users:home"},
        name="password_change",
    ),
    url(
        r"^password/reset/$",
        auth_views.password_reset,
        {"post_reset_redirect": "users:home"},
        name="password_reset",
    ),
    # Third-party --------------------------------------------------------------
    url(r"^comments/", include("django_comments.urls")),
    # TWLight apps -------------------------------------------------------------
    # This makes our custom set language form  available.
    url(r"^i18n/", include("TWLight.i18n.urls")),
    url(r"^api/", include(api_urls, namespace="api")),
    url(r"^users/", include(users_urls, namespace="users")),
    url(r"^applications/", include(applications_urls, namespace="applications")),
    url(r"^partners/", include(partners_urls, namespace="partners")),
    url(r"^csv/", include(csv_urls, namespace="csv")),
    url(r"^ezproxy/", include(ezproxy_urls, namespace="ezproxy")),
    # Other TWLight views
    url(r"^oauth/login/$", auth.OAuthInitializeView.as_view(), name="oauth_login"),
    url(r"^oauth/callback/$", auth.OAuthCallbackView.as_view(), name="oauth_callback"),
    url(r"^dashboard/$", DashboardView.as_view(), name="dashboard"),
    url(r"^terms/$", TermsView.as_view(), name="terms"),
    # For partner suggestions
    url(r"^suggest/$", PartnerSuggestionView.as_view(), name="suggest"),
    url(
        r"^suggest/(?P<pk>[0-9]+)/delete/$",
        login_required(SuggestionDeleteView.as_view()),
        name="suggest-delete",
    ),
    url(
        r"^suggest/(?P<pk>[0-9]+)/upvote/$",
        login_required(SuggestionUpvoteView.as_view()),
        name="upvote",
    ),
    # For contact us form
    url(r"^contact/$", ContactUsView.as_view(), name="contact"),
    # Cached for 24 hours.
    url(
        r"^i18n-whitelist$",
        cache_page(86400)(LanguageWhiteListView.as_view()),
        name="i18n_whitelist",
    ),
    url(r"^$", HomePageView.as_view(), name="homepage"),
    url(r"^about/$", TemplateView.as_view(template_name="about.html"), name="about"),
    url(
        r"^activity/$",
        ActivityView.as_view(),
        name="activity",
    ),
]
