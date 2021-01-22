# -*- coding: utf-8 -*-
import json

from django.views.generic import TemplateView
from django.views import View
from django.conf import settings
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from TWLight.resources.models import Partner

from django.http import HttpResponseBadRequest
from django.template import TemplateDoesNotExist, loader
from django.views.decorators.csrf import requires_csrf_token
from django.views.decorators.debug import sensitive_variables

import logging

from django.views.defaults import ERROR_400_TEMPLATE_NAME, ERROR_PAGE_TEMPLATE

logger = logging.getLogger(__name__)


class LanguageWhiteListView(View):
    """
    JSON dump of current intersection between CLDR and Django languages.
    For translatewiki.net. Cache set via decorator in urls.py.
    """

    def get(self, request):
        whitelist_dict = {}
        for i, (lang_code, autonym) in enumerate(settings.INTERSECTIONAL_LANGUAGES):
            whitelist_dict[lang_code] = autonym

        whitelist_json = json.dumps(
            whitelist_dict, ensure_ascii=False, sort_keys=True, indent=4
        )
        return HttpResponse(whitelist_json, content_type="application/json")


class HomePageView(TemplateView):

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)

        # Library bundle requirements
        # -----------------------------------------------------

        # We bundle these up into a list so that we can loop them and have a simpler time
        # setting the relevant CSS.
        if self.request.user.is_authenticated:
            editor = self.request.user.editor
            sufficient_edits = editor.wp_enough_edits
            sufficient_tenure = editor.wp_account_old_enough
            sufficient_recent_edits = editor.wp_enough_recent_edits
            not_blocked = editor.wp_not_blocked
        else:
            sufficient_edits = False
            sufficient_tenure = False
            sufficient_recent_edits = False
            not_blocked = False

        context["bundle_criteria"] = [
            # Translators: This text is shown next to a tick or cross denoting whether the current user has made more than 500 edits from their Wikimedia account.
            (_("500+ edits"), sufficient_edits),
            # Translators: This text is shown next to a tick or cross denoting whether the current user has Wikimedia account that is at least 6 months old.
            (_("6+ months editing"), sufficient_tenure),
            # Translators: This text is shown next to a tick or cross denoting whether the current user has made more than 10 edits within the last month (30 days) from their Wikimedia account.
            (_("10+ edits in the last month"), sufficient_recent_edits),
            # Translators: This text is shown next to a tick or cross denoting whether the current user's Wikimedia account has been blocked on any project.
            (_("No active blocks"), not_blocked),
        ]

        # Partner count
        # -----------------------------------------------------

        context["partner_count"] = Partner.objects.all().count()
        context["bundle_partner_count"] = Partner.objects.filter(
            authorization_method=Partner.BUNDLE
        ).count()

        # Apply section
        # -----------------------------------------------------

        context["featured_partners"] = Partner.objects.filter(featured=True)[:3]

        return context


@sensitive_variables()
@requires_csrf_token
def bad_request(request, exception, template_name=ERROR_400_TEMPLATE_NAME):
    """
    400 error handler.
    Templates: :template:`400.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_400_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseBadRequest(
            ERROR_PAGE_TEMPLATE % {"title": "Bad Request (400)", "details": ""},
            content_type="text/html",
        )
    # In django core, no exception content is passed to the template, to not disclose any sensitive information.
    # We pass in messages fetched from request data, but leave the rest behind.
    messages = get_messages(request)
    return HttpResponseBadRequest(template.render({"messages": messages}))
