"""
Views for sitewide functionality that don't fit neatly into any of the apps.
"""
from datetime import datetime
from dateutil import relativedelta
import time

from django.views.generic import TemplateView

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Editor

from .view_mixins import CoordinatorsOnly

class DashboardView(CoordinatorsOnly, TemplateView):
    """
    Allow coordinators to see metrics about the application process.
    """
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        def _get_js_timestamp(datetime):
            # Expects a date or datetime object; returns same in milliseconds
            # since the epoch. (That is the date format expected by flot.js.)
            return time.mktime(datetime.timetuple())*1000

        context = super(DashboardView, self).get_context_data(**kwargs)

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
