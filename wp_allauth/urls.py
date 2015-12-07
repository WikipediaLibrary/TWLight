from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import WikipediaProvider

urlpatterns = default_urlpatterns(WikipediaProvider)
