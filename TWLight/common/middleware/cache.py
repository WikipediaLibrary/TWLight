from django.conf import settings
from django.utils.cache import add_never_cache_headers


class NeverCacheHttpHeadersMiddleware:
    """
    Callable middleware that sets cache-control headers without impacting server-side caching
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path in settings.NEVER_CACHE_HTTP_HEADER_PATHS:
            add_never_cache_headers(response)
        return response
