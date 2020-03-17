from dateutil import relativedelta
import json
import logging
from numbers import Number
import time
import datetime

from django.contrib.auth.models import User
from django.utils import timezone

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Authorization

logger = logging.getLogger(__name__)

JSON = "json"
PYTHON = "python"

# Utilities --------------------------------------------------------------------
def get_js_timestamp(datetime):
    # Expects a date or datetime object; returns same in milliseconds
    # since the epoch. (That is the date format expected by flot.js.)
    return int(time.mktime(datetime.timetuple()) * 1000)


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
        median = int(values_list[(list_len - 1) // 2])
    else:
        median = int(
            (values_list[(list_len - 1) // 2] + values_list[1 + (list_len - 1) // 2])
            // 2
        )

    return median


def get_earliest_creation_date(queryset):
    # Some imported applications had no date and were given
    # creation dates of Jan 1, 1970. This screws up the graphs.
    if queryset:
        # Authorization creation date field is named 'date_authorized'
        if queryset.model.__name__ is "Authorization":
            earliest_date = (
                queryset.exclude(date_authorized=datetime.date(1970, 1, 1))
                .earliest("date_authorized")
                .date_authorized
            )
        else:
            earliest_date = (
                queryset.exclude(date_created=datetime.date(1970, 1, 1))
                .earliest("date_created")
                .date_created
            )
    else:
        earliest_date = None

    return earliest_date


def get_data_count_by_month(queryset, data_format=JSON):
    """
    Given a queryset, return a data series for number of queryset members over
    time: one data point per month from the beginning of the queryset until
    today. Requires that the model have a date_created property but is
    otherwise agnostic about the model.
    """
    data_series = []

    if queryset:
        earliest_date = get_earliest_creation_date(queryset)

        current_date = timezone.now().date()

        while current_date >= earliest_date:
            if data_format == JSON:
                # flot.js expects milliseconds since the epoch.
                timestamp = get_js_timestamp(current_date)
            else:
                timestamp = current_date

            # Authorization creation date field is named 'date_authorized'
            if queryset.model.__name__ is "Authorization":
                num_objs = queryset.filter(date_authorized__lte=current_date).count()
            else:
                num_objs = queryset.filter(date_created__lte=current_date).count()

            data_series.append([timestamp, num_objs])
            current_date -= relativedelta.relativedelta(months=1)

    if data_format == JSON:
        return json.dumps(data_series)
    else:
        return data_series


# Application stats ------------------------------------------------------------
def get_application_status_data(
    queryset, statuses=Application.STATUS_CHOICES, data_format=JSON
):
    """
    Returns data about the status of Applications in a queryset. By default,
    returns json in a format suitable for display as a flot.js pie chart; can
    also return CSV.
    """
    status_data = []

    for status in statuses:
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
        # Therefore we need to force translation (using unicode(_).encode('utf-8'), not
        # force_str, because we don't know what language we might be
        # dealing with.)
        status_data.append({"label": str(status[1]), "data": status_count})

    if data_format == PYTHON:
        return status_data
    else:
        # We have to use json.dumps and not just return the Python object
        # because unicode(_).encode('utf-8') will output u'' objects that will confuse
        # JavaScript.
        return json.dumps(status_data)


# User stats ------------------------------------------------------------
def get_user_language_data(queryset, data_format=JSON):
    """
    Returns data about the language settings of users in a queryset. By default,
    returns json in a format suitable for display as a flot.js pie chart; can
    also return CSV.
    """
    language_data = []

    for language in queryset.exclude(lang=None).values("lang").distinct():
        language_count = queryset.filter(lang=language["lang"]).count()
        language_data.append({"label": str(language["lang"]), "data": language_count})

    if data_format == PYTHON:
        return language_data
    else:
        return json.dumps(language_data)


def get_time_open_histogram(queryset, data_format=JSON):
    """
    Expects a queryset of closed Applications; returns data suitable for
    generating a histogram of how long the apps were open.
    """
    data_series = {}

    for app in queryset:
        if not app.status in Application.FINAL_STATUS_LIST:
            continue

        # Careful! Don't say "if not app.days_open" - that will also fail when
        # days_open=0 (that is, when the app was closed the same day that
        # it was submitted).
        if app.days_open is None:
            logger.warning(
                "Application #{pk} is closed but doesn't have a "
                "days_open value.".format(pk=app.pk)
            )
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
    output = [[k, v] for (k, v) in list(data_series.items())]

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
        earliest_date = queryset.earliest("date_created").date_created

        this_month_start = earliest_date.replace(day=1)
        next_month_start = (
            earliest_date + relativedelta.relativedelta(months=1)
        ).replace(day=1)

        while this_month_start <= timezone.now().date():
            days_to_close = list(
                Application.objects.filter(
                    status__in=Application.FINAL_STATUS_LIST,
                    date_created__gte=this_month_start,
                    date_created__lt=next_month_start,
                )
                .exclude(days_open=None)
                .values_list("days_open", flat=True)
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


def get_users_by_partner_by_month(partner, data_format=JSON):
    """
    Given a partner, return a data series for number of unique users who have
    applied for access to that particular partner over time.
    """

    data_series = []
    partner_apps = Application.objects.filter(partner=partner)

    if partner_apps:
        # Again removing undated (Jan 1 1970) applications
        earliest_date = (
            partner_apps.exclude(date_created=datetime.date(1970, 1, 1))
            .earliest("date_created")
            .date_created
        )

        current_date = timezone.now().date()

        while current_date >= earliest_date:
            if data_format == JSON:
                timestamp = get_js_timestamp(current_date)
            else:
                timestamp = current_date

            apps_to_date = Application.objects.filter(
                partner=partner, date_created__lte=current_date
            )

            unique_users = (
                User.objects.filter(editor__applications__in=apps_to_date)
                .distinct()
                .count()
            )

            data_series.append([timestamp, unique_users])
            current_date -= relativedelta.relativedelta(months=1)

    if data_format == JSON:
        return json.dumps(data_series)
    else:
        return data_series


def get_proxy_and_renewed_authorizations():
    proxy_auth = Authorization.objects.filter(
        partners__authorization_method=Partner.PROXY
    )

    renewed_auth_ids = []
    for auth in proxy_auth:
        latest_app = auth.get_latest_app()
        if latest_app.parent:
            renewed_auth_ids.append(auth.id)

    renewed_auth = proxy_auth.filter(id__in=renewed_auth_ids)
    return proxy_auth, renewed_auth
