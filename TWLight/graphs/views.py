import csv
import logging

from django.db.models import Avg
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Editor
from TWLight.view_mixins import CoordinatorsOnly

from .helpers import (get_application_status_data,
                      get_data_count_by_month,
                      get_users_by_partner_by_month,
                      get_js_timestamp,
                      get_wiki_distribution_pie_data,
                      get_wiki_distribution_bar_data,
                      get_time_open_histogram,
                      get_median_decision_time)


logger = logging.getLogger(__name__)


class DashboardView(CoordinatorsOnly, TemplateView):
    """
    Allow coordinators to see metrics about the application process.
    """
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)

        # Overall data
        # ----------------------------------------------------------------------

        context['total_apps'] = Application.objects.count()
        context['total_editors'] = Editor.objects.count()
        context['total_partners'] = Partner.objects.count()

        # Partnership data
        # ----------------------------------------------------------------------

        context['partner_time_data'] = get_data_count_by_month(
                Partner.objects.all()
            )

        # Editor data
        # ----------------------------------------------------------------------

        context['home_wiki_pie_data'] = get_wiki_distribution_pie_data()

        context['home_wiki_bar_data'] = get_wiki_distribution_bar_data()


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

        avg_days_open = float(
            closed_apps.aggregate(
                Avg('days_open')
            )['days_open__avg']
        )

        context['avg_days_open'] = avg_days_open

        # Histogram of time open -----------------------------------------------

        context['app_time_histogram_data'] = get_time_open_histogram(closed_apps)

        # Median decision time per month ---------------------------------------

        context['app_medians_data'] = get_median_decision_time(
                Application.objects.all()
            )

        # Application status pie chart -----------------------------------------

        context['app_distribution_data'] = get_application_status_data(
                Application.objects.all()
            )

        return context


# CSV-generating views ---------------------------------------------------------

# These views power "download as CSV" buttons. They provide the same data sets
# that are reflected in the DashboardView, but as HttpResponses with csv data.

class _CSVDownloadView(View):
    """
    Base view powering CSV downloads. Not intended to be used directly.
    URLs should point at subclasses of this view. Subclasses should implement a
    _write_data() method.
    """
    def get(self, request, *args, **kwargs):
        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="data.csv"'

        self._write_data(response)

        return response


    def _write_data(self):
        raise NotImplementedError



class CSVNumPartners(_CSVDownloadView):
    def _write_data(self, response):
        data = get_data_count_by_month(
                Partner.objects.all()
            )
        writer = csv.writer(response)

        writer.writerow(['Milliseconds since the epoch', 'Number of partners'])

        for row in data:
            writer.writerow(row)



class CSVHomeWikiPie(_CSVDownloadView):
    def _write_data(self, response):
        data = get_wiki_distribution_pie_data()

        writer = csv.DictWriter(response, fieldnames=['label', 'data'])

        writer.writerow({'label': 'Home wiki', 'data': 'Number of users'})

        for row in data:
            writer.writerow(row)



class CSVHomeWikiOverTime(_CSVDownloadView):
    def _write_data(self, response):
        data = get_wiki_distribution_bar_data()

        writer = csv.writer(response)

        writer.writerow(
            ['Wiki', 'Milliseconds since the epoch', 'Number of users'])

        for elem in data:
            for point in elem['data']:
                writer.writerow([elem['label'], point[0], point[1]])
