# -*- coding: utf-8 -*-
import csv
from datetime import date

# django-request analytics package, NOT requests URL library!
from request.models import Request

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.resources.factories import PartnerFactory
from TWLight.users.models import Authorization
from TWLight.users.factories import UserFactory, EditorFactory

from . import views


class GraphsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(GraphsTestCase, cls).setUpClass()
        cls.factory = RequestFactory()

        Request(path="/admin/", ip="127.0.0.1").save()
        Request(path="/admin/", ip="127.0.0.1").save()
        Request(path="/admin/login/", ip="127.0.0.1").save()

        staff_user = User.objects.create_user(username="foo", password="bar")
        staff_user.is_staff = True
        staff_user.save()
        cls.staff_user = staff_user

        user = UserFactory()
        cls.user = user

        cls.partner = PartnerFactory()

        cls.app = ApplicationFactory(partner=cls.partner)
        cls.app.status = Application.APPROVED
        cls.app.save()

        cls.dashboard_url = reverse("dashboard")

    def _verify_equal(self, resp, expected_data):
        reader_list = csv.reader(resp.content.decode("utf-8").splitlines())
        next(reader_list)  # Skip header row
        for row in reader_list:
            assert row in expected_data

        # The total number of lines in our CSV should be one more than the
        # number of lines in our expected_data (because of the header row).
        # As we've verified that all the lines in our CSV are present in our
        # expected data, we've now verified that they are identical (modulo the
        # header).
        self.assertEqual(reader_list.line_num, len(expected_data) + 1)

    def test_dashboard_view(self):
        """
        Test that the dashboard view works at all for a normal user
        who isn't currently logged in.
        """
        request = self.factory.get(self.dashboard_url)
        request.user = self.user

        response = views.DashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_average_accounts_per_user(self):
        """
        Test that the 'Average accounts per user' statistic returns the correct
        number.
        """
        # Create 3 users
        user1 = UserFactory()
        user2 = UserFactory()
        _ = UserFactory()

        # Three partners
        partner1 = PartnerFactory()
        partner2 = PartnerFactory()
        partner3 = PartnerFactory()

        # Four Authorizations
        auth1 = Authorization(user=user1)
        auth1.save()
        auth1.partners.add(partner1)
        auth2 = Authorization(user=user2)
        auth2.save()
        auth2.partners.add(partner1)
        auth3 = Authorization(user=user2)
        auth3.save()
        auth3.partners.add(partner2)
        auth4 = Authorization(user=user2)
        auth4.save()
        auth4.partners.add(partner3)

        request = self.factory.get(self.dashboard_url)
        request.user = self.user

        response = views.DashboardView.as_view()(request)
        average_authorizations = response.context_data["average_authorizations"]

        # We expect 2 authorizations (one user has 1, one has 3, average is 2)
        self.assertEqual(average_authorizations, 2)

    def test_proxy_auth_renewals_csv(self):
        """
        Test that the CSVProxyAuthAndRenewals csv download works
        """
        partner1 = PartnerFactory(authorization_method=Partner.PROXY)
        partner2 = PartnerFactory(authorization_method=Partner.PROXY)

        editor1 = EditorFactory()
        editor2 = EditorFactory()

        parent_app = ApplicationFactory(
            status=Application.SENT, partner=partner1, editor=editor1
        )
        ApplicationFactory(
            status=Application.SENT, partner=partner1, editor=editor1, parent=parent_app
        )
        ApplicationFactory(status=Application.SENT, partner=partner2, editor=editor2)

        request = self.factory.get(reverse("csv:proxy_authorizations"))
        request.user = self.user

        response = views.CSVProxyAuthRenewalRate.as_view()(request)

        expected_data = [[str(date.today()), "2", "1", "50.0%"]]
        self._verify_equal(response, expected_data)

    def test_app_time_histogram_csv(self):
        """
        Test that the CSVAppTimeHistogram csv download works
        """

        request = self.factory.get(reverse("csv:app_time_histogram"))
        request.user = self.user

        response = views.CSVAppTimeHistogram.as_view()(request)

        expected_data = [["0", "1"]]

        self._verify_equal(response, expected_data)

    def test_num_approved_applications_csv(self):
        """
        Test that the CSVNumApprovedApplications csv download works
        """

        request = self.factory.get(reverse("csv:num_applications"))
        request.user = self.user

        response = views.CSVNumApprovedApplications.as_view()(request)

        # The application was created today, so the expectation is that the
        # resulting data will be an application for today.
        expected_data = [[str(date.today()), "1"]]

        self._verify_equal(response, expected_data)

    def test_app_distribution_csv(self):
        """
        Test that the CSVAppDistribution csv download works
        """
        # Create some applications with different statuses
        for app_status in [
            Application.PENDING,
            Application.APPROVED,
            Application.QUESTION,
        ]:
            app = ApplicationFactory()
            app.status = app_status
            app.save()

        request = self.factory.get(reverse("csv:app_distribution"))
        request.user = self.user

        response = views.CSVAppDistribution.as_view()(request)

        expected_data = [
            ["Pending", "1"],
            ["Approved", "2"],
            ["Under discussion", "1"],
            ["Sent to partner", "0"],
            ["Not approved", "0"],
            ["Invalid", "0"],
        ]

        self._verify_equal(response, expected_data)

    def test_user_language_csv(self):
        """
        Test that the CSVUserLanguage csv download works
        """
        for language in ["en", "fr", "fr", "de"]:
            user = UserFactory()
            user.userprofile.lang = language
            user.userprofile.save()

        request = self.factory.get(reverse("csv:user_language"))
        request.user = self.user

        response = views.CSVUserLanguage.as_view()(request)

        expected_data = [["en", "1"], ["fr", "2"], ["de", "1"]]

        self._verify_equal(response, expected_data)

    def test_app_medians_csv(self):
        """
        Test that the CSVAppMedians csv download works
        """

        request = self.factory.get(reverse("csv:app_medians"))
        request.user = self.user

        response = views.CSVAppMedians.as_view()(request)

        # The application was created today, so the expectation is that the
        # resulting data will be an application for this month with 0 days
        # to decision (we approved it immediately).
        expected_data = [[str(date.today().replace(day=1)), "0"]]

        self._verify_equal(response, expected_data)

    def test_csv_page_views(self):
        url = reverse("csv:page_views")

        # Page view metrics are limited to staff, so make sure to use
        # RequestFactory to add a staff user to the request.
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViews.as_view()(req)

        expected_data = [["/admin/", "2"], ["/admin/login/", "1"]]

        self._verify_equal(resp, expected_data)

    def test_csv_page_views_by_path(self):
        # Try one of the paths in our responses.
        url = reverse("csv:page_views_by_path", kwargs={"path": "admin/login"})
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViewsByPath.as_view()(req, path="admin/login")

        expected_data = [["/admin/login/", "1"]]

        self._verify_equal(resp, expected_data)

        # Try the other.
        url = reverse("csv:page_views_by_path", kwargs={"path": "admin"})
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViewsByPath.as_view()(req, path="admin")

        expected_data = [["/admin/", "2"]]

        self._verify_equal(resp, expected_data)

        # Try a path we haven't hit.
        url = reverse("csv:page_views_by_path", kwargs={"path": "fake/url"})
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViewsByPath.as_view()(req, path="fake/url")

        expected_data = [["/fake/url/", "0"]]

        self._verify_equal(resp, expected_data)
