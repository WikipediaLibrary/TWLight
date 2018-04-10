# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Editor

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


        # New applications!
        apps = self._get_newest(Application.objects.all())

        for app in apps:
            event = {}
            event['icon'] = 'fa-align-left'
            event['color'] = '' # grey (default when no color class is applied)
            if app.rationale:
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
            status=Application.APPROVED, date_closed__isnull=False))

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

        return context
