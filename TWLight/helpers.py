from django.contrib.sites.models import Site
from django.conf import settings
from django.db.utils import ProgrammingError


def site_id():
    # Prefer the current initialized site.
    try:
        return Site.objects.get_current().pk
    # If don't have an initialized database yet, fetch the default from settings.
    except ProgrammingError:
        return settings.SITE_ID
