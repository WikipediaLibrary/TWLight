"""
Views for sitewide functionality that don't fit neatly into any of the apps.
"""

from django.views.generic import TemplateView

from TWLight.applications.models import Application

from .view_mixins import CoordinatorsOnly

class DashboardView(CoordinatorsOnly, TemplateView):
    """
    Allow coordinators to see metrics about the application process.
    """
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)

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
