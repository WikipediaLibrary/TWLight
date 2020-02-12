# -*- coding: utf-8 -*-
from datetime import date
from dateutil import relativedelta
import json

from django.views.generic import TemplateView
from django.views import View
from django.conf import settings
from django.http import HttpResponse

from TWLight.resources.models import Partner

import logging

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

    def _get_newest(self, queryset):
        count = queryset.count()

        if count >= 5:
            objects = queryset.order_by("-date_created")[:5]
        else:
            objects = queryset.all()

        return objects

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)

        # Library bundle requirements
        # -----------------------------------------------------

        # We bundle these up into a list so that we can loop them and have a simpler time
        # setting the relevant CSS.
        # TODO: This will need unifying/centralising with Bundle mechanism
        if self.request.user.is_authenticated():
            editor = self.request.user.editor
            sufficient_edits = editor.wp_editcount > 500
            sufficient_tenure = editor.wp_registered < date.today() + relativedelta.relativedelta(
                months=-6
            )
            sufficient_recent_edits = False  # TODO: Implement
        else:
            sufficient_edits = False
            sufficient_tenure = False
            sufficient_recent_edits = False

        context["bundle_criteria"] = [
            ("500+ edits", sufficient_edits),
            ("6+ months editing", sufficient_tenure),
            ("10+ edits in the last month", sufficient_recent_edits),
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
