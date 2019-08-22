import csv
from datetime import date
# The django-request analytics package, NOT the python URL library requests!
from request.models import Request
import logging

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import resolve
from django.contrib import messages
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, View
from django.utils.translation import ugettext as _

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import UserProfile, Authorization

from .helpers import (get_application_status_data,
                      get_data_count_by_month,
                      get_users_by_partner_by_month,
                      get_time_open_histogram,
                      get_median_decision_time,
                      get_user_language_data,
                      PYTHON)


logger = logging.getLogger(__name__)


class DashboardView(TemplateView):
    """
    Let people see metrics about the application process.
    """
    template_name = 'dashboard.html'

    def _get_partner_from_path(self, path):
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path = path + '/'

        try:
            pk = resolve(path).kwargs['pk']
        except KeyError:
            return None

        try:
            return Partner.even_not_available.get(pk=pk)
        except Partner.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)

        # Pageview data
        # ----------------------------------------------------------------------
        top_pages = Request.objects.exclude(path='/favicon.ico'
                    ).values('path'
                    ).annotate(the_count=Count('path')
                    ).order_by('-the_count')[:10]
        context['top_pages'] = top_pages

        # filter by response code to prevent the report itself from hosing.
        # 2xx reposnse codes are all valid, so this was a quick and dirty way
        # to fix the issue.  This view probably needs to be rethought.
        partner_pages = Request.objects.filter(response__startswith='2'
                    ).filter(path__startswith='/partners/'
                    ).values('path'
                    ).annotate(the_count=Count('path')
                    ).order_by('-the_count')

        partner_pages = [dict(
                            {'partner': self._get_partner_from_path(x['path'])},
                            **x
                         ) for x in partner_pages]

        context['partner_pages'] = partner_pages

        # Overall application-related data
        # ----------------------------------------------------------------------

        # Total number of approved applications
        context['total_apps'] = Application.objects.filter(
            status__in=[Application.APPROVED, Application.SENT]).count()
        # Total number of unique editors with approved applications
        context['total_editors'] = Application.objects.filter(
            status__in=[Application.APPROVED, Application.SENT]).values(
                "editor").distinct().count()

        context['total_partners'] = Partner.objects.count()

        # Average active authorizations per user, for users with at least one.
        all_authorizations = Authorization.objects.exclude(
            date_expires__lte=date.today()
        )
        authorizations_count = all_authorizations.count()
        authorized_users_count = all_authorizations.values(
            'authorized_user').distinct().count()

        # If we haven't authorized anyone yet, just show 0
        if authorized_users_count:
            # Have to add float so we don't return an int
            context['average_authorizations'] = authorizations_count/float(
                authorized_users_count)
        else:
            context['average_authorizations'] = 0

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
        
        # Total number of approved applications over time ----------------------
        context['application_time_data'] = get_data_count_by_month(
                Application.objects.filter(
                    status__in=[Application.APPROVED, Application.SENT])
            )

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
        # Exlude imported applications
        context['app_medians_data'] = get_median_decision_time(
                Application.objects.exclude(imported=True)
            )

        # Application status pie chart -----------------------------------------

        context['app_distribution_data'] = get_application_status_data(
                Application.objects.exclude(
                    status__in=(Application.NOT_APPROVED, Application.SENT)),
                    statuses=Application.STATUS_CHOICES[0:3]
            )

        # User language pie chart ----------------------------------------------

        context['user_count'] = UserProfile.objects.all().count()

        context['user_language_data'] = get_user_language_data(
            UserProfile.objects.all())

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



class CSVAppTimeHistogram(_CSVDownloadView):
    def _write_data(self, response):
        closed_apps = Application.objects.filter(
            status__in=[Application.APPROVED, Application.NOT_APPROVED]
        )

        data = get_time_open_histogram(closed_apps, data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow(
            # Translators: This is the heading of a data file which lists the number of days it took to decide on applications that have already been accepted/rejected.
            [_('Days until decision').encode('utf-8'),
             # Translators: This is the heading of a data file which lists the number of days it took to decide on applications that have already been accepted/rejected. This heading denotes the number of applicants for a particular number of days.
             _('Number of applications').encode('utf-8')])

        for row in data:
            writer.writerow(row)

            
class CSVNumApprovedApplications(_CSVDownloadView):
    def _write_data(self, response):
        queryset = Application.objects.filter(
                        status__in=[Application.APPROVED, Application.SENT])

        data = get_data_count_by_month(queryset, data_format=PYTHON)
        writer = csv.writer(response)
        # Translators: This is the heading of a data file, for a column containing date data.
        writer.writerow([_('Date').encode('utf-8'),
                         # Translators: This is the heading of a data file. 'Number of partners' refers to the total number of publishers/databases open to applications on the website.
                         _('Number of approved applications').encode('utf-8')])

        for row in data:
            writer.writerow(row)


class CSVAppMedians(_CSVDownloadView):
    def _write_data(self, response):
        # Exlude imported applications
        data = get_median_decision_time(
            Application.objects.exclude(imported=True),
            data_format=PYTHON
        )

        writer = csv.writer(response)

        writer.writerow(
            # Translators: This is the heading of a data file, denoting the column which contains the dates (months) corresponding to data collection
            [_('Month').encode('utf-8'),
             # Translators: This is the heading of a data file which lists the median (not mean) number of days until a decision (approve or reject) was made on applications.
             _('Median days until decision').encode('utf-8')])

        for row in data:
            writer.writerow(row)



class CSVAppDistribution(_CSVDownloadView):
    def _write_data(self, response):
        if 'pk' in self.kwargs:
            pk = self.kwargs['pk']
            partner = get_object_or_404(Partner.even_not_available, pk=pk)

            csv_queryset = Application.objects.filter(partner=partner)

        else:
            csv_queryset = Application.objects.all()

        data = get_application_status_data(
            csv_queryset,
            data_format=PYTHON
        )

        writer = csv.DictWriter(response, fieldnames=['label', 'data'])

        writer.writerow({'label': _('Status').encode('utf-8'),
                         'data': _('Number of applications').encode('utf-8')})

        for row in data:
            writer.writerow(row)



class CSVAppCountByPartner(_CSVDownloadView):
    def _write_data(self, response):
        pk = self.kwargs['pk']
        partner = get_object_or_404(Partner.even_not_available, pk=pk)

        queryset = Application.objects.filter(partner=partner)

        if 'approved_or_sent' in self.kwargs:
            queryset = queryset.filter(status__in=(Application.APPROVED, Application.SENT))

        data = get_data_count_by_month(queryset, data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow([_('Date').encode('utf-8'),
            # Translators: This is the heading of a data file which lists the number of applications to a partner.
            _('Number of applications').encode('utf-8')])

        for row in data:
            writer.writerow(row)



class CSVUserCountByPartner(_CSVDownloadView):
    def _write_data(self, response):
        pk = self.kwargs['pk']

        partner = get_object_or_404(Partner.even_not_available, pk=pk)

        data = get_users_by_partner_by_month(partner, data_format=PYTHON)

        writer = csv.writer(response)

        writer.writerow([_('Date').encode('utf-8'),
            # Translators: This is the heading of a data file which lists the number of unique (not counting repeat applications) users who have applied to a partner.
            _('Number of unique users who applied').encode('utf-8')])

        for row in data:
            writer.writerow(row)



class CSVPageViews(_CSVDownloadView):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super(CSVPageViews, self).dispatch(request, *args, **kwargs)
        else:
            messages.add_message (request, messages.WARNING,
                # Translators: This is a warning which is shown when a user who is not a staff member attempts to download the pageview data file.
                _('You must be staff to do that.'))
            raise PermissionDenied


    def _write_data(self, response):
        path_list = Request.objects.values('path').annotate(
            the_count=Count('path')).order_by()

        writer = csv.writer(response)
        # Translators: This is the heading for a downloadable data file showing the number of visitors to each page on the website. Page URL is the column which lists the URL of each page
        writer.writerow([_('Page URL').encode('utf-8'),
            _('Number of (non-unique) visitors').encode('utf-8')])

        for elem in path_list:
            row = [elem['path'].encode('utf-8'), elem['the_count']]
            writer.writerow(row)



class CSVPageViewsByPath(_CSVDownloadView):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super(CSVPageViewsByPath, self).dispatch(
                request, *args, **kwargs)
        else:
            messages.add_message (request, messages.WARNING,
                _('You must be staff to do that.'))
            raise PermissionDenied


    def _write_data(self, response):
        path = self.kwargs['path']

        # The captured pattern likely won't start or end with /, but the
        # database stores paths starting and ending with /.
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path = path + '/'

        path_count = Request.objects.filter(path=path).count()
        writer = csv.writer(response)

        writer.writerow([_('Page URL').encode('utf-8'),
            # Translators: This is the heading for a downloadable data file showing the number of visitors to each page on the website.
            _('Number of (non-unique) visitors').encode('utf-8')])

        row = [path.encode('utf-8'), path_count]
        writer.writerow(row)

class CSVUserLanguage(_CSVDownloadView):
    def _write_data(self, response):
        csv_queryset = UserProfile.objects.all()

        data = get_user_language_data(
            csv_queryset,
            data_format=PYTHON
        )

        writer = csv.DictWriter(response, fieldnames=['label', 'data'])

        writer.writerow({'label': _('Language').encode('utf-8'),
                         'data': _('Number of users').encode('utf-8')})

        for row in data:
            writer.writerow(row)
