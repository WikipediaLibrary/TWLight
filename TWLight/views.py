# -*- coding: utf-8 -*-
import json

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from django.views import View
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Editor
from TWLight.resources.models import AccessCode
from TWLight.view_mixins import StaffOnly

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
        
        whitelist_json = json.dumps(whitelist_dict, ensure_ascii=False, sort_keys=True, indent=4)
        return HttpResponse(whitelist_json, content_type='application/json')

class HomePageView(TemplateView):
    """
    At / , people should see recent activity.
    """
    template_name = 'home.html'

    def _get_newest(self, queryset):
        count = queryset.count()

        if count >= 5:
            objects = queryset.order_by('-date_created')[:5]
        else:
            objects = queryset.all()

        return objects


    def get_context_data(self, **kwargs):
        """
        Provide latest activity data for the front page to display.

        Each tile will need:
        * an icon
        * a color
        * text
        * a datetime
        """
        context = super(HomePageView, self).get_context_data(**kwargs)

        activity = []

        # New account signups!
        editors = self._get_newest(Editor.objects.all())

        for editor in editors:
            event = {}
            event['icon'] = 'fa-users'
            event['color'] = 'warning' # will be yellow
            # Translators: On the website front page (https://wikipedialibrary.wmflabs.org/), this message is on the timeline if a new user registers. Don't translate {username}. Translate Wikipedia Library in the same way as the global branch is named (click through from https://meta.wikimedia.org/wiki/The_Wikipedia_Library).
            event['text'] = _(u'{username} signed up for a Wikipedia Library '
                'Card Platform account').format(username=editor.wp_username)
            event['date'] = editor.date_created
            activity.append(event)

        # Newly added partners! (Available partners only.)
        partners = self._get_newest(Partner.objects.all())

        for partner in partners:
            event = {}
            event['icon'] = 'fa-files-o'
            event['color'] = 'success' # green
            # Translators: On the website front page (https://wikipedialibrary.wmflabs.org/), this message is on the timeline if a new partner is added. Don't translate {partner}. Translate Wikipedia Library in the same way as the global branch is named (click through from https://meta.wikimedia.org/wiki/The_Wikipedia_Library).
            event['text'] = _(u'{partner} joined the Wikipedia Library ').format(
                partner=partner.company_name)
            event['date'] = partner.date_created
            activity.append(event)



        # New applications! Except for the ones where the user requested
        # it be hidden.
        apps = self._get_newest(
            Application.objects.exclude(hidden=True).exclude(editor=None)
        )


        for app in apps:
            event = {}
            event['icon'] = 'fa-align-left'
            event['color'] = '' # grey (default when no color class is applied)
            if app.parent:
                # Translators: On the website front page (https://wikipedialibrary.wmflabs.org/), this message is on the timeline if a user submits a renewal request. Don't translate <a href=\"{url}\">{partner}</a><blockquote>{rationale}</blockquote>
                text = _(u'{username} applied for renewal of their ' \
                       '<a href="{url}">{partner}</a> access').format(
                            username=app.editor.wp_username,
                            partner=app.partner.company_name,
                            url=reverse_lazy('partners:detail',
                                kwargs={'pk': app.partner.pk}))
            elif app.rationale:
                # Translators: On the website front page (https://wikipedialibrary.wmflabs.org/), this message is on the timeline if a user submits an application with a rationale. Don't translate <a href=\"{url}\">{partner}</a><blockquote>{rationale}</blockquote>
                text = _(u'{username} applied for access to ' \
                       '<a href="{url}">{partner}</a>' \
                       '<blockquote>{rationale}</blockquote>').format(
                            username=app.editor.wp_username,
                            partner=app.partner.company_name,
                            url=reverse_lazy('partners:detail',
                                kwargs={'pk': app.partner.pk}),
                            rationale=app.rationale)
            else:
                # Translators: On the website front page (https://wikipedialibrary.wmflabs.org/), this message is on the timeline if a user submits an application. Don't translate <a href="{url}">{partner}</a>
                text = _(u'{username} applied for access to ' \
                       '<a href="{url}">{partner}</a>').format(
                            username=app.editor.wp_username,
                            partner=app.partner.company_name,
                            url=reverse_lazy('partners:detail',
                                kwargs={'pk': app.partner.pk}))

            event['text'] = text
            event['date'] = app.date_created
            activity.append(event)

        # New access grants!
        grants = self._get_newest(Application.objects.filter(
            status=Application.APPROVED, date_closed__isnull=False).exclude(
                editor=None))

        for grant in grants:
            event = {}
            event['icon'] = 'fa-align-left'
            event['color'] = 'info' # light blue
            # Translators: On the website front page (https://wikipedialibrary.wmflabs.org/), this message is on the timeline if an application is accepted. Don't translate <a href="{url}">{partner}</a>.
            event['text'] = _(u'{username} received access to '
                '<a href="{url}">{partner}</a>').format(
                    username=grant.editor.wp_username,
                    partner=grant.partner.company_name,
                    url=reverse_lazy('partners:detail',
                        kwargs={'pk': grant.partner.pk}))
            event['date'] = grant.date_closed
            activity.append(event)

        try:
            context['activity'] = sorted(activity,
                key=lambda x: x['date'],
                reverse=True)
        except TypeError:
            # If we don't have any site activity yet, we'll get an exception.
            context['activity'] = []

        # Featured partners
        # -----------------------------------------------------

        context['featured_partners'] = Partner.objects.filter(
            featured=True).order_by('company_name')

        # Partner count
        # -----------------------------------------------------

        context['partner_count'] = Partner.objects.all().count()
        
        return context

class StaffDashboardView(StaffOnly, View):

    def get(self, request, *args, **kwargs):
        return render(request, 'staff.html')

    def post(self, request, *args, **kwargs):
        # This code was based on the guide at
        # https://www.pythoncircle.com/post/30/how-to-upload-and-process-the-csv-file-in-django/
        uploaded_csv = request.FILES['access_code_csv']
        staff_url = reverse_lazy('staff')

        if not uploaded_csv.name.endswith('.csv'):
            # Translators: When staff upload a file containing access codes, it must be a .csv file. This error message is shown if it is any other file type.
            messages.error(request, _('File must be a csv'))
            return HttpResponseRedirect(staff_url)

        # Check against the maximum upload size (2.5mb by default)
        if uploaded_csv.multiple_chunks():
            # Translators: When staff upload a file containing access codes, they receive this error message if the file size is too large.
            messages.error(request, _("Uploaded file is too large."))
            return HttpResponseRedirect(staff_url)

        file_data = uploaded_csv.read().decode('utf-8')

        lines = file_data.split("\n")

        skipped_codes = 0
        num_codes = 0
        # Validate the entire file before trying to save any of it
        for line_num, line in enumerate(lines):
            fields = line.split(",")
            num_columns = len(fields)
            # Skip any blank lines. Not an error, can just be ignored.
            if line == '':
                continue
            if num_columns != 2:
                # Translators: When staff upload a file containing access codes, they receive this message if a line in the file has more than 2 pieces of data.
                messages.error(request, _("Line {line_num} has {num_columns} columns. "
                               "Expected 2.".format(line_num=line_num+1,
                                    num_columns=num_columns)))
                return HttpResponseRedirect(staff_url)

            access_code = fields[0].strip()
            try:
                partner_pk = int(fields[1].strip())
            except ValueError:
                messages.error(request, _("Second column should only contain "
                    "numbers. Error on line {line_num}.".format(
                        line_num=line_num+1)))
                return HttpResponseRedirect(staff_url)

            try:
                check_partner = Partner.even_not_available.get(pk=partner_pk)
            except ObjectDoesNotExist:
                # Translators: When staff upload a file containing access codes, they receive this message if a partner ID in the file doesn't correspond to a partner in the Library Card platform database.
                messages.error(request, _("File contains reference to invalid "
                    "partner ID on line {line_num}".format(line_num=line_num+1)))
                return HttpResponseRedirect(staff_url)

            # Only upload this code if it doesn't already exist. If it does,
            # increment a counter so we can report that.
            access_code_partner_check = AccessCode.objects.filter(code=access_code,
                partner=partner_pk).count()
            if access_code_partner_check != 0:
                skipped_codes += 1
            else:
                new_access_code = AccessCode()
                new_access_code.code = access_code
                new_access_code.partner = Partner.even_not_available.get(pk=partner_pk)
                new_access_code.save()
                num_codes += 1

        if num_codes > 0:
            # Translators: When staff successfully upload a file containing access codes, they receive this message.
            messages.info(request, _("{num_codes} access codes successfully "
                "uploaded!".format(num_codes=num_codes)))
        if skipped_codes > 0:
            # Translators: When staff upload a file containing access codes, they receive this message if any were duplicates.
            messages.info(request, _("{num_duplicates} access codes ignored "
                "as duplicates.".format(num_duplicates=skipped_codes)))
        return HttpResponseRedirect(staff_url)
