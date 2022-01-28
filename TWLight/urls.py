"""
TWLight URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/ref/urls/
"""
import sys
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.admindocs import urls as admindocs
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_page

from TWLight.api.urls import urlpatterns as api_urls
from TWLight.applications.urls import urlpatterns as applications_urls
from TWLight.emails.views import ContactUsView
from TWLight.resources.urls import urlpatterns as partners_urls
from TWLight.resources.views import (
    PartnerSuggestionView,
    SuggestionDeleteView,
    SuggestionMergeView,
    SuggestionUpvoteView,
)
from TWLight.users import oauth as auth
from TWLight.users.urls import urlpatterns as users_urls
from TWLight.users.views import TermsView
from TWLight.ezproxy.urls import urlpatterns as ezproxy_urls

from .views import NewHomePageView, SearchEndpointFormView

handler400 = "TWLight.views.bad_request"

urlpatterns = [
    # Built-in -----------------------------------------------------------------
    url(r"^admin/doc", include(admindocs)),
    url(r"^admin/", admin.site.urls),
    url(r"^accounts/login/", auth_views.LoginView.as_view(), name="auth_login"),
    url(
        r"^accounts/logout/",
        auth_views.LogoutView.as_view(),
        {"next_page": "/"},
        name="auth_logout",
    ),
    url(
        r"^password/change/$",
        auth_views.PasswordChangeView.as_view(),
        {"post_change_redirect": "users:home"},
        name="password_change",
    ),
    url(
        r"^password/reset/$",
        auth_views.PasswordResetView.as_view(),
        {"post_reset_redirect": "users:home"},
        name="password_reset",
    ),
    # Third-party --------------------------------------------------------------
    url(r"^comments/", include("django_comments.urls")),
    # TWLight apps -------------------------------------------------------------
    # This makes our custom set language form  available.
    url(r"^i18n/", include("TWLight.i18n.urls")),
    url(r"^api/", include((api_urls, "api"), namespace="api")),
    url(r"^users/", include((users_urls, "users"), namespace="users")),
    url(
        r"^applications/",
        include((applications_urls, "applications"), namespace="applications"),
    ),
    url(r"^partners/", include((partners_urls, "resources"), namespace="partners")),
    url(r"^ezproxy/", include((ezproxy_urls, "ezproxy"), namespace="ezproxy")),
    # Other TWLight views
    url(r"^oauth/login/$", auth.OAuthInitializeView.as_view(), name="oauth_login"),
    url(r"^oauth/callback/$", auth.OAuthCallbackView.as_view(), name="oauth_callback"),
    url(r"^terms/$", TermsView.as_view(), name="terms"),
    # For partner suggestions
    url(r"^suggest/$", PartnerSuggestionView.as_view(), name="suggest"),
    url(r"^suggest/merge/$", SuggestionMergeView.as_view(), name="suggest-merge"),
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
    url(r"^$", NewHomePageView.as_view(), name="homepage"),
    url(r"^about/$", TemplateView.as_view(template_name="about.html"), name="about"),
    url(
        r"^search/$",
        login_required(SearchEndpointFormView.as_view()),
        name="search",
    ),
]

# Enable debug_toolbar if configured
if (
    settings.TWLIGHT_ENV == "local"
    and settings.REQUIREMENTS_FILE == "debug.txt"
    and (settings.DEBUG or "test" in sys.argv)
):
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    # To better debug and improve the error pages, we are making them pages
    # available when django debug toolbar is enabled
    urlpatterns += [
        url(r"^400/$", TemplateView.as_view(template_name="400.html")),
        url(r"^403/$", TemplateView.as_view(template_name="403.html")),
        url(r"^404/$", TemplateView.as_view(template_name="404.html")),
        url(r"^500/$", TemplateView.as_view(template_name="500/500.html")),
    ]
