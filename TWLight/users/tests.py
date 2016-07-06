# -*- coding: utf-8 -*-
from urlparse import urlparse

from django.contrib.auth.models import User
from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.test import TestCase, Client

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application

from .helpers.wiki_list import WIKIS
from .factories import EditorFactory
from .groups import get_coordinators

# Should be replaced with a proper factory, but factory-boy plus new migrations
# infrastructure doesn't seem to work right in tests.


def get_or_create_user(userpass):
    """
    create_user() lets us set the password directly, but will throw an
    IntegrityError if a user with the username already exists.
    get_or_create() lets us check to see if the user exists already, but
    the password field contains the salted hash. Sigh. Let's make a
    utility that checks for existence AND lets us set the pw.
    """
    user, _ = User.objects.get_or_create(username=userpass)
    user.set_password(userpass)
    user.save()
    return user


class ViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        # User 1: regular Editor
        self.username1 = 'alice'
        self.user1 = get_or_create_user(self.username1)
        self.editor1 = EditorFactory(user=self.user1)
        self.url1 = reverse('users:editor_detail',
            kwargs={'pk': self.editor1.pk})


        # User 2: regular Editor
        self.username2 = 'bob'
        self.user2 = get_or_create_user(self.username2)
        self.editor2 = EditorFactory(user=self.user2)
        self.url2 = reverse('users:editor_detail',
            kwargs={'pk': self.editor2.pk})


        # User 3: Site administrator
        self.username3 = 'carol'
        self.user3 = get_or_create_user(self.username3)
        self.user3.is_superuser = True
        self.user3.save()
        self.editor3 = EditorFactory(user=self.user3)


        # User 4: Coordinator
        self.username4 = 'eve'
        self.user4 = get_or_create_user(self.username4)
        self.editor4 = EditorFactory(user=self.user4)
        get_coordinators().user_set.add(self.user4)


    def tearDown(self):
        self.user1.delete()
        self.editor1.delete()
        self.user2.delete()
        self.editor2.delete()
        self.user3.delete()
        self.editor3.delete()
        self.user4.delete()
        self.editor4.delete()


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
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1, follow=True)
        self.assertEqual(response.status_code, 200)


    def test_editor_cannot_see_other_editor_page(self):
        """Editors cannot see other editors' pages."""
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url2, follow=True)
        self.assertEqual(response.status_code, 403)


    def test_coordinator_access(self):
        """Coordinators can see someone else's page."""
        self.client.login(username=self.username4, password=self.username4)
        response = self.client.get(self.url1, follow=True)
        self.assertEqual(response.status_code, 200)


    def test_site_admin_can_see_other_editor_page(self):
        """Site admins can see someone else's page."""
        self.client.login(username=self.username3, password=self.username3)
        response = self.client.get(self.url1, follow=True)
        self.assertEqual(response.status_code, 200)


    def test_editor_page_has_editor_data(self):
        """Expected editor personal data is in their page."""
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1, follow=True)
        content = response.content

        # This uses default data from EditorFactory.
        self.assertIn('wp_alice', content)                 # wp_username
        self.assertContains(response, '42')             # edit count
        self.assertIn('some groups', content)           # wp_groups
        self.assertIn('some rights', content)           # wp_rights
        self.assertIn(WIKIS[0][0], content)             # home wiki
        self.assertIn('Cat floofing, telemetry, fermentation', content)


    def test_editor_page_has_application_history(self):
        """Expected editor application data is in their page."""
        app1 = ApplicationFactory(status=Application.PENDING, editor=self.user1.editor)
        app2 = ApplicationFactory(status=Application.QUESTION, editor=self.user1.editor)
        app3 = ApplicationFactory(status=Application.APPROVED, editor=self.user1.editor)
        app4 = ApplicationFactory(status=Application.NOT_APPROVED, editor=self.user1.editor)

        expected_html = render_to_string(
            'applications/application_list_include.html',
            {'object_list': [app1, app2, app3, app4]}
            )

        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1, follow=True)
        self.assertContains(response, expected_html)


# TODO write these tests after design review
# Test user creation
# receiving signal from oauth results in creation of editor model
# site admin status is false
# editor model contains all expected info (mock out the signal)

# Terms of use
# After login they should be redirected to agreement page if not agreed
# Likewise for request-for-application
# Also for the application page itself
