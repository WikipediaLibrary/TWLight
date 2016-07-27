from dateutil import relativedelta
import json
import logging
from numbers import Number
import time

from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.encoding import force_unicode

from TWLight.applications.models import Application
from TWLight.users.helpers.wiki_list import WIKIS
from TWLight.users.models import Editor


logger = logging.getLogger(__name__)

JSON = 'json'
PYTHON = 'python'

# Utilities --------------------------------------------------------------------
def get_js_timestamp(datetime):
    # Expects a date or datetime object; returns same in milliseconds
    # since the epoch. (That is the date format expected by flot.js.)
    return int(time.mktime(datetime.timetuple())*1000)


def get_median(values_list):
    """Given a list (of numbers), returns its median value."""
    try:
        for item in values_list:
            assert isinstance(item, Number)
    except AssertionError:
        return 0

    values_list.sort()
    list_len = len(values_list)

    if list_len < 1:
        # Mathematically bogus, but will make graph display correctly.
        median = 0
    elif list_len % 2 == 1:
        median = int(values_list[(list_len - 1 )/2])
    else:
        median = int((values_list[(list_len - 1 )/2] +
                       values_list[1 + (list_len -1 )/2]) / 2)

    return median


def get_data_count_by_month(queryset, data_format=JSON):
    """
    Given a queryset, return a data series for number of queryset members over
    time: one data point per month from the beginning of the queryset until
    today. Requires that the model have a date_created property but is
    otherwise agnostic about the model.
    """
    data_series = []

    if queryset:
        earliest_date = queryset.earliest('date_created').date_created

        current_date = timezone.now().date()

        while current_date >= earliest_date:
            if data_format == JSON:
                # flot.js expects milliseconds since the epoch.
                timestamp = get_js_timestamp(current_date)
            else:
                timestamp = current_date

            num_objs = queryset.filter(date_created__lte=current_date).count()
            data_series.append([timestamp, num_objs])
            current_date -= relativedelta.relativedelta(months=1)

    if data_format == JSON:
        return json.dumps(data_series)
    else:
        return data_series


# Application stats ------------------------------------------------------------
def get_application_status_data(queryset, data_format=JSON):
    """
    Returns data about the status of Applications in a queryset. By default,
    returns json in a format suitable for display as a flot.js pie chart; can
    also return CSV.
    """
    status_data = []

    for status in Application.STATUS_CHOICES:
        status_count = queryset.filter(status=status[0]).count()
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

    if data_format == PYTHON:
        return status_data
    else:
        # We have to use json.dumps and not just return the Python object
        # because force_unicode will output u'' objects that will confuse
        # JavaScript.
        return json.dumps(status_data)


def get_time_open_histogram(queryset, data_format=JSON):
    """
    Expects a queryset of closed Applications; returns data suitable for
    generating a histogram of how long the apps were open.
    """
    data_series = {}

    for app in queryset:
        if not app.status in [Application.APPROVED, Application.NOT_APPROVED]:
            continue

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
    # flot.
    output = [[k, v] for (k, v) in data_series.items()]

    if data_format == JSON:
        return json.dumps(output)
    else:
        return output


def get_median_decision_time(queryset, data_format=JSON):
    """
    Expects a queryset of Applications; returns data suitable for graphing
    mean decision time.
    """
    data_series = []

    if queryset:
        earliest_date = queryset.earliest('date_created').date_created

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

            if data_format == JSON:
                js_timestamp = get_js_timestamp(this_month_start)
                data_series.append([js_timestamp, median_days])
            else:
                data_series.append([this_month_start, median_days])

            next_month_start += relativedelta.relativedelta(months=1)
            this_month_start += relativedelta.relativedelta(months=1)

    if data_format == JSON:
        return json.dumps(data_series)
    else:
        return data_series


# User stats ------------------------------------------------------------
def get_wiki_distribution_pie_data(data_format=JSON):
    wiki_data = []

    for wiki in WIKIS:
        editor_count = Editor.objects.filter(home_wiki=wiki[0]).count()
        if editor_count:
            wiki_data.append({'label': wiki[1], 'data': editor_count})

    # The table will make the most sense if it puts the most popular wikis
    # on top.
    output = sorted(wiki_data, key=lambda x: x['data'], reverse=True)

    if data_format == JSON:
        return json.dumps(output)
    else:
        return output


def get_wiki_distribution_bar_data(data_format=JSON):
    def _add_home_wiki_bar_chart_point(data_series, datestamp):
        if data_format == JSON:
            timestamp = get_js_timestamp(datestamp)
        else:
            timestamp = datestamp

        for wiki in WIKIS:
            num_editors = Editor.objects.filter(
                home_wiki=wiki[0], date_created__lte=datestamp).count()
            data_series[wiki[1]].insert(0, [timestamp, num_editors])

        return data_series

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
    output = [{'label': wiki, 'data': data_series[wiki]}
            for wiki in data_series
            if data_series[wiki][-1][1]]

    if data_format == JSON:
        return json.dumps(output)
    else:
        return output


def get_users_by_partner_by_month(partner, data_format=JSON):
    """
    Given a partner, return a data series for number of unique users who have
    applied for access to that particular partner over time.
    """

    data_series = []
    partner_apps = Application.objects.filter(partner=partner)

    if partner_apps:
        earliest_date = partner_apps.earliest('date_created').date_created

        current_date = timezone.now().date()

        while current_date >= earliest_date:
            if data_format == JSON:
                timestamp = get_js_timestamp(current_date)
            else:
                timestamp = current_date

            apps_to_date = Application.objects.filter(
                partner=partner,
                date_created__lte=current_date)

            unique_users = User.objects.filter(
                editor__applications__in=apps_to_date).distinct().count()

            data_series.append([timestamp, unique_users])
            current_date -= relativedelta.relativedelta(months=1)

    if data_format == JSON:
        return json.dumps(data_series)
    else:
        return data_series
