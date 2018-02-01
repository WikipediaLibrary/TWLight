# -*- coding: utf-8 -*-
import copy
from datetime import datetime, timedelta
import json
from mock import patch, Mock
from urlparse import urlparse

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.test import TestCase, Client, RequestFactory
from django.utils.translation import get_language

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application

from . import views
from .authorization import OAuthBackend
from .helpers.wiki_list import WIKIS, LANGUAGE_CODES
from .factories import EditorFactory, UserFactory
from .groups import get_coordinators
from .models import UserProfile, Editor


FAKE_IDENTITY_DATA = {'query': {
    'userinfo': {
        'options': {
            'disablemail': 0
            }
        }
    }
}

FAKE_IDENTITY = {
    'editcount': 5000,
    'registered': '20151106154629', # Well before first commit.
    'blocked': False,
    'iss': urlparse(settings.TWLIGHT_OAUTH_PROVIDER_URL).scheme + urlparse(settings.TWLIGHT_OAUTH_PROVIDER_URL).netloc,
    'sub': 567823,
    'rights': ['deletion', 'spaceflight', 'autoconfirmed'],
    'groups': ['charismatic megafauna'],
    'email': 'alice@example.com',
    'username': 'alice',
}

FAKE_GLOBAL_USERINFO = {
    'home': 'enwiki',
    'id': 567823,
    'registration': '2015-11-06T15:46:29Z', # Well before first commit.
    'name': 'alice',
    'editcount': 5000,
}

class ViewsTestCase(TestCase):

    def setUp(self):
        super(ViewsTestCase, self).setUp()
        self.client = Client()

        # User 1: regular Editor
        self.username1 = 'alice'
        self.user_editor = UserFactory(username=self.username1)
        self.editor1 = EditorFactory(user=self.user_editor)
        self.url1 = reverse('users:editor_detail',
            kwargs={'pk': self.editor1.pk})


        # User 2: regular Editor
        self.username2 = 'bob'
        self.user_editor2 = UserFactory(username=self.username2)
        self.editor2 = EditorFactory(user=self.user_editor2)
        self.url2 = reverse('users:editor_detail',
            kwargs={'pk': self.editor2.pk})


        # User 3: Site administrator
        self.username3 = 'carol'
        self.user_superuser = UserFactory(username=self.username3)
        self.user_superuser.is_superuser = True
        self.user_superuser.save()
        self.editor3 = EditorFactory(user=self.user_superuser)


        # User 4: Coordinator
        self.username4 = 'eve'
        self.user_coordinator = UserFactory(username=self.username4)
        self.editor4 = EditorFactory(user=self.user_coordinator)
        get_coordinators().user_set.add(self.user_coordinator)

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        self.message_patcher = patch('TWLight.applications.views.messages.add_message')
        self.message_patcher.start()



    def tearDown(self):
        super(ViewsTestCase, self).tearDown()
        self.user_editor.delete()
        self.editor1.delete()
        self.user_editor2.delete()
        self.editor2.delete()
        self.user_superuser.delete()
        self.editor3.delete()
        self.user_coordinator.delete()
        self.editor4.delete()
        self.message_patcher.stop()


    def test_editor_detail_url_resolves(self):
        """
        The EditorDetailView resolves.
        """
        _ = resolve(self.url1)


    def test_anon_user_cannot_see_editor_details(self):
        """
        If an AnonymousUser hits an editor page, they are redirected to login.
        """
        response = self.client.get(self.url1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path,
            settings.LOGIN_URL)


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

        # Make sure the editor is not a coordinator, because coordinators *can*
        # see others' pages!
        coordinators = get_coordinators()
        try:
            assert self.user_editor not in coordinators.user_set.all()
        except AssertionError:
            coordinators.user_set.remove(self.user_editor)

        with self.assertRaises(PermissionDenied):
            _ = views.EditorDetailView.as_view()(request, pk=self.editor2.pk)


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

        # This uses default data from EditorFactory, except for the username,
        # which is randomly generated (hence has no default).
        self.assertIn(self.editor1.wp_username, content)
        self.assertIn('42', content)
        self.assertIn('Cat floofing, telemetry, fermentation', content)


    def test_editor_page_has_application_history(self):
        """Expected editor application oauth_data is in their page."""
        app1 = ApplicationFactory(status=Application.PENDING, editor=self.user_editor.editor)
        app2 = ApplicationFactory(status=Application.QUESTION, editor=self.user_editor.editor)
        app3 = ApplicationFactory(status=Application.APPROVED, editor=self.user_editor.editor)
        app4 = ApplicationFactory(status=Application.NOT_APPROVED, editor=self.user_editor.editor)

        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_editor

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)

        self.assertEqual(set(response.context_data['object_list']),
            set([app1, app2, app3, app4]))
        content = response.render().content

        self.assertIn(app1.__str__(), content)
        self.assertIn(app2.__str__(), content)
        self.assertIn(app3.__str__(), content)
        self.assertIn(app4.__str__(), content)

        # We can't use assertTemplateUsed with RequestFactory (only with
        # Client), and testing that the rendered content is equal to an
        # expected string is too fragile.


    def test_user_home_view_anon(self):
        """
        If an AnonymousUser hits UserHomeView, they are redirected to login.
        """
        factory = RequestFactory()
        request = factory.get(reverse('users:home'))
        request.user = AnonymousUser()

        response = views.UserHomeView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path,
            settings.LOGIN_URL)


    def test_user_home_view_is_editor(self):
        """
        If a User who is an editor hits UserHomeView, they see EditorDetailView.
        """
        user = UserFactory()
        editor = EditorFactory(user=user)

        factory = RequestFactory()

        home_request = factory.get(reverse('users:home'))
        home_request.user = user
        home_response = views.UserHomeView.as_view()(home_request)

        detail_request = factory.get(reverse('users:editor_detail',
            kwargs={'pk': editor.pk}))
        detail_request.user = user
        detail_response = views.EditorDetailView.as_view()(detail_request, pk=editor.pk)

        # We can't actually check that EditorDetailView was used by UserHomeView
        # directly, because its as_view function has already been processed
        # and all we have access to is a return value. So let's check that the
        # output of the two pages is the same - the user would have seen the
        # same thing on either page.
        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(home_response.render().content,
            detail_response.render().content)


    @patch('TWLight.users.views.UserDetailView.as_view')
    def test_user_home_view_non_editor(self, mock_view):
        """
        A User who isn't an editor hitting UserHomeView sees UserDetailView.
        """
        user = UserFactory(username='not_an_editor')
        self.assertFalse(hasattr(user, 'editor'))

        factory = RequestFactory()

        request = factory.get(reverse('users:home'))
        request.user = user
        _ = views.UserHomeView.as_view()(request)

        # For this we can't even check that the rendered content is the same,
        # because we don't have a URL allowing us to render UserDetailView
        # correctly; we'll mock out its as_view function and make sure it got
        # called.
        mock_view.assert_called_once_with()



class UserProfileModelTestCase(TestCase):
    def test_user_profile_created(self):
        """
        UserProfile should be created on user creation.
        """
        user = UserFactory()

        # If the signal has not created a UserProfile, this line will throw
        # a DoesNotExist and the test will fail, which is what we want.
        UserProfile.objects.get(user=user)

        user.delete()


    def test_user_profile_sets_tou_to_false(self):
        # Don't use UserFactory, since it forces the related profile to have
        # agreed to the terms for simplicity in most tests! Use the user
        # creation function that we actually use in production.
        user = User.objects.create_user(username='profiler',
            email='profiler@example.com')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.terms_of_use, False)

        user.delete()


    def test_user_profile_sets_use_wp_email_to_true(self):
        """
        Verify that UserProfile.use_wp_email defaults to True.
        (Editor.update_from_wikipedia assumes this to be the case.)
        """
        user = User.objects.create_user(username='profiler',
            email='profiler@example.com')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.use_wp_email, True)

        user.delete()



class EditorModelTestCase(TestCase):

    def setUp(self):
        super(EditorModelTestCase, self).setUp()
        for editor in Editor.objects.all():
            # The test case succeeds when runs alone but fails when run
            # as part of the whole suite, because it grabs the wrong editor
            # object from the db. Kill them all with fire.
            # (Why does it do this? Because our queries look for editors by
            # username or wikipedia sub, not by foreign key - we have to use the
            # information that we have from the wikipedia API, which knows
            # nothing about our database. But the test runner doesn't actually
            # *delete* database objects between runs, for performance reasons;
            # it simply truncates them by nulling out their foreign keys.
            # This means that if you are searching for db objects by properties
            # other than foreign key, you *still find them*.)
            editor.delete()

        # Wiki 'zh-classical' is 'zh-classical.wikipedia.org'. It's also the
        # longest wiki name in wiki_list.
        self.test_editor = EditorFactory(wp_username='editor_model_test',
            wp_rights=json.dumps(['cat floofing', 'the big red button']),
            wp_groups=json.dumps(['sysops', 'bureaucrats']))


    def tearDown(self):
        super(EditorModelTestCase, self).tearDown()
        self.test_editor.delete()


    def test_wp_user_page_url(self):
        expected_url = settings.TWLIGHT_OAUTH_PROVIDER_URL + '/User:editor_model_test'
        self.assertEqual(expected_url, self.test_editor.wp_user_page_url)


    def test_wp_link_sul_info(self):
        expected_url = 'https://tools.wmflabs.org/quentinv57-tools/tools/sulinfo.php?username=editor_model_test'
        self.assertEqual(expected_url, self.test_editor.wp_link_sul_info)


    def test_get_wp_rights_display(self):
        expected_text = ['cat floofing', 'the big red button']
        self.assertEqual(expected_text, self.test_editor.get_wp_rights_display)


    def test_get_wp_groups_display(self):
        expected_text = ['sysops', 'bureaucrats']
        self.assertEqual(expected_text, self.test_editor.get_wp_groups_display)


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

        oauth_data = FAKE_IDENTITY_DATA

        global_userinfo_data = FAKE_GLOBAL_USERINFO

        # This goes to an iterator; we need to return the expected data
        # enough times to power all the calls to read() in this function.
        mock_response.read.side_effect = [json.dumps(oauth_data)] * 7

        mock_urllib2.return_value = mock_response

        identity = copy.copy(FAKE_IDENTITY)
        global_userinfo = copy.copy(FAKE_GLOBAL_USERINFO)

        # Valid data
        self.assertTrue(self.test_editor._is_user_valid(identity, global_userinfo))

        # Edge case
        global_userinfo['editcount'] = 500
        self.assertTrue(self.test_editor._is_user_valid(identity, global_userinfo))

        # Too few edits
        global_userinfo['editcount'] = 499
        self.assertFalse(self.test_editor._is_user_valid(identity, global_userinfo))

        # Account created too recently
        global_userinfo['editcount'] = 500
        identity['registered'] = datetime.today().strftime('%Y%m%d%H%M%S')
        self.assertFalse(self.test_editor._is_user_valid(identity, global_userinfo))

        # Edge case: this shouldn't.
        almost_6_months_ago = datetime.today() - timedelta(days=183)
        identity['registered'] = almost_6_months_ago.strftime('%Y%m%d%H%M%S')
        self.assertTrue(self.test_editor._is_user_valid(identity, global_userinfo))

        # Edge case: this should work.
        almost_6_months_ago = datetime.today() - timedelta(days=182)
        identity['registered'] = almost_6_months_ago.strftime('%Y%m%d%H%M%S')
        self.assertTrue(self.test_editor._is_user_valid(identity, global_userinfo))

        # Bad editor! No biscuit.
        identity['blocked'] = True
        self.assertFalse(self.test_editor._is_user_valid(identity, global_userinfo))


    @patch.object(Editor, 'get_global_userinfo')
    @patch.object(Editor, '_is_user_valid')
    def test_update_from_wikipedia(self, mock_validity, mock_global_userinfo):
        # update_from_wikipedia calls _is_user_valid, which generates an API
        # call to Wikipedia that we don't actually want to do in testing.
        mock_validity.return_value = True

        identity = {}
        identity['username'] = 'evil_dr_porkchop'
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity['sub'] = self.test_editor.wp_sub
        identity['rights'] = ['deletion', 'spaceflight']
        identity['groups'] = ['charismatic megafauna']
        # We should now be ignoring the oauth editcount
        identity['editcount'] = 42
        identity['email'] = 'porkchop@example.com'
        identity['iss'] = 'zh-classical.wikipedia.org'
        identity['registered'] = '20130205230142'

        global_userinfo = {}
        global_userinfo['home'] = 'zh_classicalwiki'
        global_userinfo['id'] = identity['sub']
        global_userinfo['registration'] = '2013-02-05T23:01:42Z'
        global_userinfo['name'] = identity['username']
        # We should now be using the global_userinfo editcount
        global_userinfo['editcount'] = 960

        # update_from_wikipedia calls get_global_userinfo, which generates an
        # API call to Wikipedia that we don't actually want to do in testing.
        mock_global_userinfo.return_value = global_userinfo

        # Don't change self.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory()

        lang = get_language()
        new_editor.update_from_wikipedia(identity, lang) # This call also saves the edito

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
            identity['sub'] = self.test_editor.wp_sub + 1
            new_editor.update_from_wikipedia(identity, lang) # This call also saves the edito



class AuthorizationTestCase(TestCase):

    def setUp(self):
        super(AuthorizationTestCase, self).setUp()
        # Prevent failures due to side effects from database artifacts.
        for editor in Editor.objects.all():
            editor.delete()


    @patch('urllib2.urlopen')
    def test_create_user_and_editor(self, mock_urllib2):
        """
        OAuthBackend._create_user_and_editor() should:
        * create a user
            * with a suitable username and email
            * without a password
        * And a matching editor
        """
        oauth_backend = OAuthBackend()
        oauth_data = FAKE_IDENTITY_DATA
        identity = FAKE_IDENTITY

        mock_response = Mock()
        mock_response.read.side_effect = [json.dumps(oauth_data)] * 7
        mock_urllib2.return_value = mock_response

        user, editor = oauth_backend._create_user_and_editor(identity)

        self.assertEqual(user.email, 'alice@example.com')
        self.assertEqual(user.username, '567823')
        self.assertFalse(user.has_usable_password())

        self.assertEqual(editor.user, user)
        self.assertEqual(editor.wp_sub, 567823)
        # We won't test the fields set by update_from_wikipedia, as they are
        # tested elsewhere.


    # We mock out this function for two reasons:
    # 1) To prevent its call to an external API, which we would have otherwise
    #    had to mock anyway;
    # 2) So we can assert that it was called.
    @patch('TWLight.users.models.Editor.update_from_wikipedia')
    def test_get_and_update_user_from_identity_existing_user(self, mock_update):
        """
        OAuthBackend._get_and_update_user_from_identity() should:
        * If there is an Editor whose wp_sub = identity['sub']:
            * Return the user FKed onto that
            * Return created = False
        * Call Editor.update_from_wikipedia
        """
        # Make sure the test user has the username and language anticipated by our backend.
        username = FAKE_IDENTITY['sub']
        lang = get_language()
        existing_user = UserFactory(username=username)
        params = {
            'user': existing_user,
            'wp_sub': FAKE_IDENTITY['sub']
        }

        _ = EditorFactory(**params)

        oauth_backend = OAuthBackend()
        user, created = oauth_backend._get_and_update_user_from_identity(
            FAKE_IDENTITY)

        self.assertFalse(created)
        self.assertTrue(hasattr(user, 'editor'))
        self.assertEqual(user, existing_user)

        mock_update.assert_called_once_with(FAKE_IDENTITY, lang)


    @patch('TWLight.users.models.Editor.update_from_wikipedia')
    def test_get_and_update_user_from_identity_new_user(self, mock_update):
        """
        OAuthBackend._get_and_update_user_from_identity() should:
        * Otherwise:
            * Return a new user
            * Return created = True
        * Call Editor.update_from_wikipedia
        """
        oauth_backend = OAuthBackend()
        identity = copy.copy(FAKE_IDENTITY)
        lang = get_language()
        new_sub = 57381037
        new_username = oauth_backend._get_username(identity)
        identity['sub'] = new_sub
        self.assertFalse(Editor.objects.filter(wp_sub=new_sub).count())

        user, created = oauth_backend._get_and_update_user_from_identity(
            identity)

        self.assertTrue(created)
        self.assertTrue(hasattr(user, 'editor'))
        self.assertEqual(user.editor.wp_sub, new_sub)

        mock_update.assert_called_once_with(identity, lang)



class TermsTestCase(TestCase):

    def test_terms_page_displays(self):
        """
        Terms page should display for authenticated users.

        We had a bug where attempting to view the page caused a 500 error.
        """
        _ = User.objects.create_user(username='termstestcase', password='bar')
        url = reverse('terms')

        c = Client()
        c.login(username='termstestcase', password='bar')
        response = c.get(url)

        self.assertEqual(response.status_code, 200)



class HelpersTestCase(TestCase):
    """
    We list some things in .helpers.wiki_list, but we should test to make
    sure they are kept in sync.

    Formats:
        WIKIS:              ('ab', 'ab.wikipedia.org')
        LANGUAGE_CODES:     'ab': 'Abkhazian'
    """

    def test_wikis_match_language_codes(self):
        WIKIS_LANGUAGES = set([wiki[0] for wiki in WIKIS])
        LANGUAGES = set(LANGUAGE_CODES.keys())

        self.assertEqual(WIKIS_LANGUAGES, LANGUAGES)
