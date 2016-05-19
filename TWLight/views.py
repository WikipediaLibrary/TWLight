"""
Views for sitewide functionality that don't fit neatly into any of the apps.
"""
from dateutil import relativedelta
import json
import logging
import time

from django.db.models import Avg
from django.views.generic import TemplateView
from django.utils import timezone
from django.utils.encoding import force_unicode

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.helpers.wiki_list import WIKIS
from TWLight.users.models import Editor

from .view_mixins import CoordinatorsOnly


logger = logging.getLogger(__name__)


def get_median(values_list):
    """Given a list (of numbers), returns its median value."""
    values_list.sort()
    list_len = len(values_list)

    if list_len < 1:
        # Mathematically bogus, but will make graph display correctly.
        median = 0
    elif list_len % 2 == 1:
        median = int(values_list[(list_len - 1 )/2])
    else:
        median = int((values_list[(list_len -1 )/2] +
                       values_list[1 + (list_len -1 )/2]) / 2)

    return median


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

        while month < timezone.now().date():
            # flot.js expects milliseconds since the epoch.
            js_timestamp = _get_js_timestamp(month)
            num_partners = Partner.objects.filter(date_created__lte=month).count()
            data_series.append([js_timestamp, num_partners])
            month += relativedelta.relativedelta(months=1)

        data_series.append([
            _get_js_timestamp(timezone.now().date()),
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
        month = timezone.now().date()

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


        # Application data
        # ----------------------------------------------------------------------

        # The application that has been waiting the longest for a final status
        # determination. -------------------------------------------------------
        context['longest_open'] = Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION]
            ).earliest('date_created')

        # Average number of days until a final decision gets made on an
        # application. ---------------------------------------------------------

        closed_apps = Application.objects.filter(
                status__in=[Application.APPROVED, Application.NOT_APPROVED]
            )

        avg_days_open = float(closed_apps.aggregate(Avg('days_open'))['days_open__avg'])

        context['avg_days_open'] = avg_days_open

        # Histogram of time open -----------------------------------------------

        data_series = {}

        for app in closed_apps:
            if not app.days_open:
                logger.warning("Application #{pk} is closed but doesn't have a "
                    "days_open value.".format(pk=app.pk))
            else:
                # They're stored as longs, which breaks flot.js's data
                # expectations. But if we actually *need* a long int rather than
                # an int to store the number of days until an app decision is
                # reached, we have other problems.
                int_days_open = int(app.days_open)
                if int_days_open in data_series:
                    data_series[int_days_open] += 1
                else:
                    data_series[int_days_open] = 1

        # Reformat dict (easy to use in Python) into list-of-lists expected by
        # float.
        context['app_time_histogram_data'] = [[k, v] for (k, v) in data_series.items()]

        # Median decision time per month ---------------------------------------

        data_series = []
        earliest_date = Application.objects.earliest('date_created').date_created

        this_month_start = earliest_date.replace(day=1)
        next_month_start = (earliest_date + \
            relativedelta.relativedelta(months=1)).replace(day=1)

        while this_month_start <= timezone.now().date():
            days_to_close = list(
                Application.objects.filter(
                    status__in=[Application.APPROVED, Application.NOT_APPROVED],
                    date_created__gte=this_month_start,
                    date_created__lt=next_month_start
                ).values_list('days_open', flat=True)
            )

            median_days = get_median(days_to_close)

            js_timestamp = _get_js_timestamp(this_month_start)
            data_series.append([js_timestamp, median_days])

            next_month_start += relativedelta.relativedelta(months=1)
            this_month_start += relativedelta.relativedelta(months=1)

        context['app_medians_data'] = data_series

        # Application status pie chart -----------------------------------------

        status_data = []

        for status in Application.STATUS_CHOICES:
            status_count = Application.objects.filter(status=status[0]).count()
            # We have to force unicode here because we used ugettext_lazy, not
            # ugettext, to internationalize the status labels in
            # TWLight.applications.models.
            # We had to use ugettext_lazy because the order in which Django
            # initializes objects means the system will fail on startup if we
            # try to use ugettext.
            # However, ugettext_lazy returns a reference to the translated
            # string, not the actual translation string. That reference is not
            # suitable for use in templates, and inserting it directly into the
            # javascript like this means that we bypass places that would
            # usually translate the string.
            # Therefore we need to force translation (using force_unicode, not
            # force_str, because we don't know what language we might be
            # dealing with.)
            status_data.append({'label': force_unicode(status[1]), 'data': status_count})

        # We have to use json.dumps and not just return the Python object
        # because force_unicode will output u'' objects that will confuse
        # JavaScript.
        context['app_distribution_data'] = json.dumps(status_data)

        return context
