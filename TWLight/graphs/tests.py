import csv
# django-request analytics package, NOT requests URL library!
from request.models import Request

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from . import views

class GraphsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(GraphsTestCase, cls).setUpClass()
        cls.factory = RequestFactory()

        Request(path='/admin/', ip='127.0.0.1').save()
        Request(path='/admin/', ip='127.0.0.1').save()
        Request(path='/admin/login/', ip='127.0.0.1').save()

        user = User.objects.create_user(username='foo', password='bar')
        user.is_staff = True
        user.save()
        cls.staff_user = user


    def _verify_equal(self, resp, expected_data):
        reader_list = csv.reader(resp.content.splitlines())
        reader_list.next() # Skip header row
        for row in reader_list:
            assert row in expected_data

        # The total number of lines in our CSV should be one more than the
        # number of lines in our expected_data (because of the header row).
        # As we've verified that all the lines in our CSV are present in our
        # expected data, we've now verified that they are identical (modulo the
        # header).
        self.assertEqual(reader_list.line_num, len(expected_data) + 1)


    def test_csv_page_views(self):
        url = reverse('csv:page_views')

        # Page view metrics are limited to staff, so make sure to use
        # RequestFactory to add a staff user to the request.
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViews.as_view()(req)

        expected_data = [['/admin/', '2'], ['/admin/login/', '1']]

        self._verify_equal(resp, expected_data)


    def test_csv_page_views_by_path(self):
        # Try one of the paths in our responses.
        url = reverse('csv:page_views_by_path', kwargs={'path': 'admin/login'})
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViewsByPath.as_view()(req, path='admin/login')

        expected_data = [['/admin/login/', '1']]

        self._verify_equal(resp, expected_data)

        # Try the other.
        url = reverse('csv:page_views_by_path', kwargs={'path': 'admin'})
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViewsByPath.as_view()(req, path='admin')

        expected_data = [['/admin/', '2']]

        self._verify_equal(resp, expected_data)

        # Try a path we haven't hit.
        url = reverse('csv:page_views_by_path', kwargs={'path': 'fake/url'})
        req = self.factory.get(url)
        req.user = self.staff_user

        resp = views.CSVPageViewsByPath.as_view()(req, path='fake/url')

        expected_data = [['/fake/url/', '0']]

        self._verify_equal(resp, expected_data)
