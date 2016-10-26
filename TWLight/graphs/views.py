import csv
import logging

from django.db.models import Avg
from django.http import HttpResponse
from django.views.generic import TemplateView, View
from django.utils.translation import ugettext as _

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Editor

from .helpers import (get_application_status_data,
                      get_data_count_by_month,
                      get_users_by_partner_by_month,
                      get_js_timestamp,
                      get_wiki_distribution_pie_data,
                      get_wiki_distribution_bar_data,
                      get_time_open_histogram,
                      get_median_decision_time,
                      PYTHON)


logger = logging.getLogger(__name__)


class DashboardView(TemplateView):
    """
    Let people see metrics about the application process.
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

        # Although normally we'd want JSON for graphs, the pie chart can consume
        # a normal dict, and the for loop to create the table requires a dict,
        # not JSON.
        context['home_wiki_pie_data'] = get_wiki_distribution_pie_data(
            data_format=PYTHON)

        context['home_wiki_bar_data'] = get_wiki_distribution_bar_data()


        # Application data
        # ----------------------------------------------------------------------

        # The application that has been waiting the longest for a final status
        # determination. -------------------------------------------------------
        try:
            app = Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION]
            ).earliest('date_created')
        except Application.DoesNotExist:
            app = None

        context['longest_open'] = app

        # Average number of days until a final decision gets made on an
        # application. ---------------------------------------------------------

        closed_apps = Application.objects.filter(
                status__in=[Application.APPROVED, Application.NOT_APPROVED]
            )

        average_duration = closed_apps.aggregate(
                Avg('days_open')
            )['days_open__avg']

        if average_duration:
            avg_days_open = float(average_duration)
        else:
            avg_days_open = None

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


    def _write_data(self, response):
        raise NotImplementedError



class CSVNumPartners(_CSVDownloadView):
    def _write_data(self, response):
        if 'pk' in self.kwargs:
            pk = self.kwargs['pk']

            try:
                queryset = Partner.objects.get(pk=pk)
            except Partner.DoesNotExist:
                logger.exception('Tried to access data for partner #{pk}, who '
                                 'does not exist'.format(pk=pk))
                raise

        else:
            queryset =Partner.objects.all()

        data = get_data_count_by_month(queryset, data_format=PYTHON)
        writer = csv.writer(response)

        writer.writerow([_('Date'), _('Number of partners')])

        for row in data:
            writer.writerow(row)



class CSVHomeWikiPie(_CSVDownloadView):
    def _write_data(self, response):
        data = get_wiki_distribution_pie_data(data_format=PYTHON)

        writer = csv.DictWriter(response, fieldnames=['label', 'data'])

        writer.writerow({'label': _('Home wiki'), 'data': _('Number of users')})

        for row in data:
            writer.writerow(row)



class CSVHomeWikiOverTime(_CSVDownloadView):
    def _write_data(self, response):
        data = get_wiki_distribution_bar_data(data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow(
            [_('Wiki'), _('Date'), _('Number of users')])

        for elem in data:
            for point in elem['data']:
                writer.writerow([elem['label'], point[0], point[1]])



class CSVAppTimeHistogram(_CSVDownloadView):
    def _write_data(self, response):
        closed_apps = Application.objects.filter(
            status__in=[Application.APPROVED, Application.NOT_APPROVED]
        )

        data = get_time_open_histogram(closed_apps, data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow(
            # Translators: the number of days it took to decide on applications that have already been accepted/rejected.
            [_('Days until decision'), _('Number of applications')])

        for row in data:
            writer.writerow(row)



class CSVAppMedians(_CSVDownloadView):
    def _write_data(self, response):
        data = get_median_decision_time(
            Application.objects.all(),
            data_format=PYTHON
        )

        writer = csv.writer(response)

        writer.writerow(
            [_('Month'), _('Median days until decision')])

        for row in data:
            writer.writerow(row)



class CSVAppDistribution(_CSVDownloadView):
    def _write_data(self, response):
        data = get_application_status_data(
            Application.objects.all(),
            data_format=PYTHON
        )

        writer = csv.DictWriter(response, fieldnames=['label', 'data'])

        writer.writerow({'label': _('Status'),
                         'data': _('Number of applications')})

        for row in data:
            writer.writerow(row)



class CSVAppCountByPartner(_CSVDownloadView):
    def _write_data(self, response):
        pk = self.kwargs['pk']
        try:
            partner = Partner.objects.get(pk=pk)
        except Partner.DoesNotExist:
            logger.exception('Tried to access data for partner #{pk}, who '
                             'does not exist'.format(pk=pk))
            raise

        queryset = Application.objects.filter(partner=partner)

        if 'approved' in self.kwargs:
            queryset = queryset.filter(status=Application.APPROVED)

        data = get_data_count_by_month(queryset, data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow([_('Date'),
            _('Number of applications to {partner}').format(partner=partner)])

        for row in data:
            writer.writerow(row)



class CSVUserCountByPartner(_CSVDownloadView):
    def _write_data(self, response):
        pk = self.kwargs['pk']

        try:
            partner = Partner.objects.get(pk=pk)
        except Partner.DoesNotExist:
            logger.exception('Tried to access data for partner #{pk}, who '
                             'does not exist'.format(pk=pk))
            raise

        data = get_users_by_partner_by_month(partner, data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow([_('Date'),
            _('Number of unique users who have applied to {partner}').format(partner=partner)])

        for row in data:
            writer.writerow(row)
