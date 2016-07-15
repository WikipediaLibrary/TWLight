# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json
from mock import patch, Mock
from urlparse import urlparse

from django.contrib.auth.models import User
from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.test import TestCase, Client, RequestFactory

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application

from . import views
from .helpers.wiki_list import WIKIS
from .factories import EditorFactory, UserFactory
from .groups import get_coordinators
from .models import UserProfile

class ViewsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Client()

        # User 1: regular Editor
        cls.username1 = 'alice'
        cls.user_editor = UserFactory(username=cls.username1)
        cls.editor1 = EditorFactory(user=cls.user_editor)
        cls.url1 = reverse('users:editor_detail',
            kwargs={'pk': cls.editor1.pk})


        # User 2: regular Editor
        cls.username2 = 'bob'
        cls.user_editor2 = UserFactory(username=cls.username2)
        cls.editor2 = EditorFactory(user=cls.user_editor2)
        cls.url2 = reverse('users:editor_detail',
            kwargs={'pk': cls.editor2.pk})


        # User 3: Site administrator
        cls.username3 = 'carol'
        cls.user_superuser = UserFactory(username=cls.username3)
        cls.user_superuser.is_superuser = True
        cls.user_superuser.save()
        cls.editor3 = EditorFactory(user=cls.user_superuser)


        # User 4: Coordinator
        cls.username4 = 'eve'
        cls.user_coordinator = UserFactory(username=cls.username4)
        cls.editor4 = EditorFactory(user=cls.user_coordinator)
        get_coordinators().user_set.add(cls.user_coordinator)

    @classmethod
    def tearDownClass(cls):
        cls.user_editor.delete()
        cls.editor1.delete()
        cls.user_editor2.delete()
        cls.editor2.delete()
        cls.user_superuser.delete()
        cls.editor3.delete()
        cls.user_coordinator.delete()
        cls.editor4.delete()


    def test_editor_detail_url_resolves(self):
        """
        The EditorDetailView resolves.
        """
        _ = resolve(self.url1)


    def test_anon_user_cannot_see_editor_details(self):
        """Check that an anonymous user cannot see an editor page."""
        response_url = self.client.get(self.url1).url

        url_components = urlparse(response_url)
        permission_url = reverse('users:test_permission')
        self.assertEqual(url_components.path, permission_url)


    def test_editor_can_see_own_page(self):
        """Check that editors can see their own pages."""
        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_editor

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)
        self.assertEqual(response.status_code, 200)


    def test_editor_cannot_see_other_editor_page(self):
        """Editors cannot see other editors' pages."""
        factory = RequestFactory()
        request = factory.get(self.url2)
        request.user = self.user_editor

        response = views.EditorDetailView.as_view()(request, pk=self.editor2.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path,
            reverse('users:test_permission'))


    def test_coordinator_access(self):
        """Coordinators can see someone else's page."""
        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_coordinator

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)
        self.assertEqual(response.status_code, 200)


    def test_site_admin_can_see_other_editor_page(self):
        """Site admins can see someone else's page."""
        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_superuser

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)
        self.assertEqual(response.status_code, 200)


    def test_editor_page_has_editor_data(self):
        """Expected editor personal data is in their page."""
        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_editor

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)

        content = response.render().content

        # This uses default data from EditorFactory.
        self.assertIn('wp_alice', content)
        self.assertIn('42', content)
        self.assertIn('some groups', content)           # wp_groups
        self.assertIn('some rights', content)           # wp_rights
        self.assertIn(WIKIS[0][0], content)             # home wiki
        self.assertIn('Cat floofing, telemetry, fermentation', content)


    def test_editor_page_has_application_history(self):
        """Expected editor application data is in their page."""
        app1 = ApplicationFactory(status=Application.PENDING, editor=self.user_editor.editor)
        app2 = ApplicationFactory(status=Application.QUESTION, editor=self.user_editor.editor)
        app3 = ApplicationFactory(status=Application.APPROVED, editor=self.user_editor.editor)
        app4 = ApplicationFactory(status=Application.NOT_APPROVED, editor=self.user_editor.editor)

        expected_html = render_to_string(
            'applications/application_list_include.html',
            {'object_list': [app1, app2, app3, app4]}
            )

        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_editor

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)

        content = response.render().content
        self.assertIn(expected_html, content)



class UserProfileModelTestCase(TestCase):
    def test_user_profile_created(self):
        """
        UserProfile should be created on user creation.
        """
        user = UserFactory()

        # If the signal has not created a UserProfile, this line will throw
        # a DoesNotExist and the test will fail, which is what we want.
        UserProfile.objects.get(user=user)


    def test_user_profile_has_desired_properties(self):
        # Don't use UserFactory, since it forces the related profile to have
        # agreed to the terms for simplicity in most tests! Use the user
        # creation function that we actually use in production.
        user = User.objects.create_user(username='profiler',
            email='profiler@example.com')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.terms_of_use, False)



class EditorModelTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        # Wiki 'aa' is 'aa.wikipedia.org'
        cls.editor = EditorFactory(home_wiki='aa',
            wp_username='alice',
            wp_rights=json.dumps(['cat floofing', 'the big red button']),
            wp_groups=json.dumps(['sysops', 'bureaucrats']))


    @classmethod
    def tearDownClass(cls):
        cls.editor.delete()


    def test_wp_user_page_url(self):
        expected_url = 'https://aa.wikipedia.org/wiki/User:alice'
        self.assertEqual(expected_url, self.editor.wp_user_page_url)


    def test_wp_link_edit_count(self):
        expected_url = 'https://tools.wmflabs.org/xtools-ec/?user=alice&project=aa.wikipedia.org'
        self.assertEqual(expected_url, self.editor.wp_link_edit_count)


    def test_wp_link_sul_info(self):
        expected_url = 'https://tools.wmflabs.org/quentinv57-tools/tools/sulinfo.php?username=alice'
        self.assertEqual(expected_url, self.editor.wp_link_sul_info)


    def test_wp_link_pages_created(self):
        expected_url = 'https://tools.wmflabs.org/xtools/pages/index.php?user=alice&project=aa.wikipedia.org&namespace=all&redirects=none'
        self.assertEqual(expected_url, self.editor.wp_link_pages_created)


    def test_get_wp_rights_display(self):
        expected_text = ['cat floofing', 'the big red button']
        self.assertEqual(expected_text, self.editor.get_wp_rights_display)


    def test_get_wp_groups_display(self):
        expected_text = ['sysops', 'bureaucrats']
        self.assertEqual(expected_text, self.editor.get_wp_groups_display)


    @patch('urllib2.urlopen')
    def test_is_user_valid(self, mock_urllib2):
        """
        Users must:
        * Have >= 500 edits
        * Be active for >= 6 months
        * Have Special:Email User enabled
        * Not be blocked on any projects

        This checks everything except Special:Email. (Checking that requires
        another http request, so we're going to mock a successful request here
        in order to check all the other criteria, and check for the failure case
        in the next test.)
        """
        mock_response = Mock()

        data = {}
        data['query'] = {}
        data['query']['userinfo'] = {}
        data['query']['userinfo']['options'] = {}
        data['query']['userinfo']['options']['disablemail'] = 0

        # This goes to an iterator; we need to return the expected data
        # enough times to power all the calls to read() in this function.
        mock_response.read.side_effect = [json.dumps(data)] * 7

        mock_urllib2.return_value = mock_response

        identity = {}
        identity['editcount'] = 5000
        identity['registered'] = '20151106154629' # Well before first commit.
        identity['blocked'] = False
        identity['iss'] = 'en.wikipedia.org'

        # Valid data
        self.assertTrue(self.editor._is_user_valid(identity))

        # Edge case
        identity['editcount'] = 500
        self.assertTrue(self.editor._is_user_valid(identity))

        # Too few edits
        identity['editcount'] = 499
        self.assertFalse(self.editor._is_user_valid(identity))

        # Account created too recently
        identity['editcount'] = 500
        identity['registered'] = datetime.today().strftime('%Y%m%d%H%M%S')
        self.assertFalse(self.editor._is_user_valid(identity))

        # Edge case: this shouldn't.
        almost_6_months_ago = datetime.today() - timedelta(days=183)
        identity['registered'] = almost_6_months_ago.strftime('%Y%m%d%H%M%S')
        self.assertTrue(self.editor._is_user_valid(identity))

        # Edge case: this should work.
        almost_6_months_ago = datetime.today() - timedelta(days=182)
        identity['registered'] = almost_6_months_ago.strftime('%Y%m%d%H%M%S')
        self.assertTrue(self.editor._is_user_valid(identity))

        # Bad editor! No biscuit.
        identity['blocked'] = True
        self.assertFalse(self.editor._is_user_valid(identity))


    @patch('urllib2.urlopen')
    def test_is_user_valid_2(self, mock_urllib2):
        """
        Users must:
        * Have >= 500 edits
        * Be active for >= 6 months
        * Have Special:Email User enabled
        * Not be blocked on any projects
        """
        mock_response = Mock()

        data = {}
        data['query'] = {}
        data['query']['userinfo'] = {}
        data['query']['userinfo']['options'] = {}
        data['query']['userinfo']['options']['disablemail'] = 1 # Should fail.

        mock_response.read.side_effect = [json.dumps(data)]
        mock_response.read.side_effect = [json.dumps(data)]
        mock_urllib2.return_value = mock_response

        identity = {}
        identity['editcount'] = 5000
        identity['registered'] = '20151106154629' # Well before first commit.
        identity['blocked'] = False
        identity['iss'] = 'en.wikipedia.org'

        self.assertFalse(self.editor._is_user_valid(identity))


    @patch('TWLight.users.models.Editor._is_user_valid')
    def test_update_from_wikipedia(self, mock_validity):
        # update_from_wikipedia calls _is_user_valid, which generates an API
        # call to Wikipedia that we don't actually want to do in testing.
        mock_validity.return_value = True

        # Don't change cls.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory()

        identity = {}
        identity['username'] = 'evil_dr_porkchop'
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity['sub'] = self.editor.wp_sub
        identity['rights'] = ['deletion', 'spaceflight']
        identity['groups'] = ['charismatic megafauna']
        identity['editcount'] = 960
        identity['email'] = 'porkchop@example.com'
        identity['iss'] = 'aa.wikipedia.org'
        identity['registered'] = '20130205230142'

        new_editor.update_from_wikipedia(identity)

        self.assertEqual(new_editor.wp_username, 'evil_dr_porkchop')
        self.assertEqual(new_editor.wp_rights,
            json.dumps(['deletion', 'spaceflight']))
        self.assertEqual(new_editor.wp_groups,
            json.dumps(['charismatic megafauna']))
        self.assertEqual(new_editor.wp_editcount, 960)
        self.assertEqual(new_editor.user.email, 'porkchop@example.com')
        self.assertEqual(new_editor.wp_registered,
            datetime(2013, 02, 05).date())

        # Now check what happens if their wikipedia ID number has changed - this
        # should throw an error as we can no longer verify they're the same
        # editor.
        with self.assertRaises(AssertionError):
            identity['sub'] = self.editor.wp_sub + 1
            new_editor.update_from_wikipedia(identity)


# TODO write these tests after design review
# receiving signal from oauth results in creation of editor model
# site admin status is false
# editor model contains all expected info (mock out the signal)

# Terms of use
# After login they should be redirected to agreement page if not agreed
# Likewise for request-for-application
# Also for the application page itself
