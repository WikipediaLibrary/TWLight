# -*- coding: utf-8 -*-
import json

from django.views.generic import TemplateView
from django.views import View
from django.conf import settings
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils.translation import get_language, gettext_lazy as _
from django.template import TemplateDoesNotExist, loader
from django.views.decorators.csrf import requires_csrf_token
from django.views.decorators.debug import sensitive_variables

from TWLight.resources.models import Partner, PartnerLogo
from TWLight.resources.helpers import get_partner_description, get_tag_dict

import logging

from django.views.defaults import ERROR_400_TEMPLATE_NAME, ERROR_PAGE_TEMPLATE
from TWLight.forms import SetLanguageForm

logger = logging.getLogger(__name__)


class NewHomePageView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bundle_criteria"] = [
            # Translators: This text is shown next to a tick or cross denoting whether the current user has made more than 500 edits from their Wikimedia account.
            _("500+ edits"),
            # Translators: This text is shown next to a tick or cross denoting whether the current user has Wikimedia account that is at least 6 months old.
            _("6+ months editing"),
            # Translators: This text is shown next to a tick or cross denoting whether the current user has made more than 10 edits within the last month (30 days) from their Wikimedia account.
            _("10+ edits in the last month"),
            # Translators: This text is shown next to a tick or cross denoting whether the current user's Wikimedia account has been blocked on any project.
            _("No active blocks"),
        ]

        language_code = get_language()
        translated_tags = get_tag_dict(language_code)

        if len(translated_tags) > 9:
            context["tags"] = dict(list(translated_tags.items())[0:9])
            context["more_tags"] = dict(
                list(translated_tags.items())[10 : len(translated_tags)]
            )
        else:
            context["tags"] = translated_tags
            context["more_tags"] = None

        partners_obj = []
        try:
            tags = self.request.GET.get("tags")
            if tags:
                # Since multidisciplinary partners may have content that users may
                # find useful, we are filtering by the multidisciplinary tag as well
                tag_filter = Q(new_tags__tags__contains=tags) | Q(
                    new_tags__tags__contains="multidisciplinary_tag"
                )
                # This variable is to indicate which tag filter has been selected
                context["selected"] = tags
                # It is harder to get only one tag value from a dictionary in a
                # template, so we are getting the translated tag value in the view
                context["selected_value"] = translated_tags[tags]
            else:
                tag_filter = Q(featured=True)
        except KeyError:
            tag_filter = Q(featured=True)

        # Partners will appear ordered by the selected tag first, then by the
        # multidisciplinary tag
        if tags:
            # Order by ascending tag order if tag name is before multidisciplinary
            if tags < "multidisciplinary_tag":
                partners = Partner.objects.filter(tag_filter).order_by(
                    "new_tags__tags", "?"
                )
            # Order by descending tag order if tag name is after multidisciplinary
            else:
                partners = Partner.objects.filter(tag_filter).order_by(
                    "-new_tags__tags", "?"
                )
        # No tag filter was passed, ordering can be random
        else:
            partners = Partner.objects.filter(tag_filter).order_by("?")

        for partner in partners:
            # Obtaining translated partner description
            partner_short_description_key = "{pk}_short_description".format(
                pk=partner.pk
            )
            partner_description_key = "{pk}_description".format(pk=partner.pk)
            partner_descriptions = get_partner_description(
                language_code, partner_short_description_key, partner_description_key
            )
            try:
                partner_logo = partner.logos.logo.url
            except PartnerLogo.DoesNotExist:
                partner_logo = None
            partners_obj.append(
                {
                    "pk": partner.pk,
                    "partner_name": partner.company_name,
                    "partner_logo": partner_logo,
                    "short_description": partner_descriptions["short_description"],
                    "description": partner_descriptions["description"],
                }
            )
        context["partners"] = partners_obj
        context["language_form"] = SetLanguageForm()

        return context

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/users/my_library")
        else:
            context = self.get_context_data()
            return render(request, "homepage.html", context)


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
