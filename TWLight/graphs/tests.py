import csv
# django-request analytics package, NOT requests URL library!
from request.models import Request

from django.core.urlresolvers import reverse
from django.test import TestCase, Client


class GraphsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(GraphsTestCase, cls).setUpClass()
        cls.client = Client()
        Request(path='/admin/', ip='127.0.0.1').save()
        Request(path='/admin/', ip='127.0.0.1').save()
        Request(path='/admin/login/', ip='127.0.0.1').save()


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
        resp = self.client.get(url)

        expected_data = [['/admin/', '2'], ['/admin/login/', '1']]

        self._verify_equal(resp, expected_data)


    def test_csv_page_views_by_path(self):
        # Try one of the paths in our responses.
        url = reverse('csv:page_views_by_path', kwargs={'path': 'admin/login'})
        resp = self.client.get(url)

        expected_data = [['/admin/login/', '1']]

        self._verify_equal(resp, expected_data)

        # Try the other.
        url = reverse('csv:page_views_by_path', kwargs={'path': 'admin'})
        resp = self.client.get(url)

        expected_data = [['/admin/', '2']]

        self._verify_equal(resp, expected_data)

        # Try a path we haven't hit.
        url = reverse('csv:page_views_by_path', kwargs={'path': 'fake/url'})
        resp = self.client.get(url)

        expected_data = [['/fake/url/', '0']]

        self._verify_equal(resp, expected_data)
