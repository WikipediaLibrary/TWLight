"""
Views for sitewide functionality that don't fit neatly into any of the apps.
"""
from datetime import datetime
from dateutil import relativedelta
import json
import time

from django.views.generic import TemplateView

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.helpers.wiki_list import WIKIS
from TWLight.users.models import Editor

from .view_mixins import CoordinatorsOnly

class DashboardView(CoordinatorsOnly, TemplateView):
    """
    Allow coordinators to see metrics about the application process.
    """
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)

        # Helper functions
        # ----------------------------------------------------------------------

        def _get_js_timestamp(datetime):
            # Expects a date or datetime object; returns same in milliseconds
            # since the epoch. (That is the date format expected by flot.js.)
            return int(time.mktime(datetime.timetuple())*1000)

        def _add_home_wiki_bar_chart_point(data_series, datestamp):
            js_timestamp = _get_js_timestamp(datestamp)
            for wiki in WIKIS:
                num_editors = Editor.objects.filter(
                    home_wiki=wiki[0], date_created__lte=datestamp).count()
                data_series[wiki[1]].insert(0, [js_timestamp, num_editors])

            return data_series


        # Overall data
        # ----------------------------------------------------------------------

        context['total_apps'] = Application.objects.count()
        context['total_editors'] = Editor.objects.count()
        context['total_partners'] = Partner.objects.count()   

        # Partnership data
        # ----------------------------------------------------------------------

        # Build up a data series for number of partners over time: one data
        # point per month since the first partner, plus one data point for
        # today.
        data_series = []
        earliest_date = Partner.objects.earliest('date_created').date_created

        month = earliest_date

        while month < datetime.today().date():
            # flot.js expects milliseconds since the epoch.
            js_timestamp = _get_js_timestamp(month)
            num_partners = Partner.objects.filter(date_created__lte=month).count()
            data_series.append([js_timestamp, num_partners])
            month += relativedelta.relativedelta(months=1)

        data_series.append([
            _get_js_timestamp(datetime.today().date()),
            Partner.objects.count()
        ])

        context['partner_time_data'] = data_series


        # Editor data
        # ----------------------------------------------------------------------

        # Pie chart of home wiki distribution ----------------------------------

        wiki_data = []

        for wiki in WIKIS:
            editor_count = Editor.objects.filter(home_wiki=wiki[0]).count()
            if editor_count:
                wiki_data.append({'label': wiki[1], 'data': editor_count})

        # The table will make the most sense if it puts the most popular wikis
        # on top.
        wiki_data = sorted(wiki_data, key=lambda x: x['data'], reverse=True)

        context['home_wiki_pie_data'] = wiki_data

        # Bar chart of home wiki distribution over time ------------------------

        data_series = {wiki[1]: [] for wiki in WIKIS}

        earliest_date = Editor.objects.earliest('date_created').date_created
        month = datetime.today().date()

        while month >= earliest_date:
            # We're going to go backwards from today rather than forward
            # from the beginning of time because we want to include today, but
            # the bar graph will look nicest if all the intervals are even -
            # if we started at the earliest_date and added a month each time,
            # today's data would be appended at some probably-not-month-long
            # interval.
            data_series = _add_home_wiki_bar_chart_point(data_series, month)

            month -= relativedelta.relativedelta(months=1)

        # Here we reformat our data_series (which has been a dict, for ease of
        # manipulation in Python) into the list of {label, data} dicts expected
        # by flot.js.
        # While we're at it, we remove any home wikis with zero editors, as
        # they'd just clutter up the graph without adding information.
        # Because the number of editors per wiki strictly increases over time
        # (as accounts are added), we can do this by simply looking at the
        # editor count in the last data point for any given wiki and seeing if
        # it is nonzero.
        home_wiki_bar_data = [{'label': wiki, 'data': data_series[wiki]}
                              for wiki in data_series
                              if data_series[wiki][-1][1]]
        context['home_wiki_bar_data'] = home_wiki_bar_data


        # Misc
        # ----------------------------------------------------------------------

        # The application that has been waiting the longest for a final status
        # determination.
        context['longest_open'] = Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION]
            ).earliest('date_created')

        # Average number of days until a final decision gets made on an
        # application. This really wants to be a query using F expressions
        # inside aggregate(), but that isn't implemented until Django 1.8.
        closed_apps = Application.objects.filter(
                status__in=[Application.APPROVED, Application.NOT_APPROVED]
            )

        total_seconds_open = reduce(lambda h, app:
            h + (app.date_closed - app.date_created).total_seconds(),
            closed_apps, 0)

        avg_days_open = int(round((total_seconds_open / (closed_apps.count()))/86400, 0))
        context['avg_days_open'] = avg_days_open

        return context
