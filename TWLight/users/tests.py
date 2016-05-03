from urlparse import urlparse

from django.conf import settings
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


    # EditorDetailView resolves at URL
    def test_editor_detail_url_resolves(self):
        """
        The EditorDetailView resolves.
        """
        _ = resolve(self.url1)


    # Anonymous user cannot see editor page
    def test_anon_user_cannot_see_editor_details(self):
        response_url = self.client.get(self.url1).url

        url_components = urlparse(response_url)
        self.assertEqual(url_components.path, settings.LOGIN_URL)


    # Editor can see own page
    def test_editor_can_see_own_page(self):
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1, follow=True)
        self.assertEqual(response.status_code, 200)


    # Editor cannot see someone else's info
    def test_editor_cannot_see_other_editor_page(self):
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url2, follow=True)
        self.assertEqual(response.status_code, 403)


    # Coordinator can see someone else's info
    def test_coordinator_access(self):
        self.client.login(username=self.username4, password=self.username4)
        response = self.client.get(self.url1, follow=True)
        self.assertEqual(response.status_code, 200)


    # Site admin can see someone else's info
    def test_site_admin_can_see_other_editor_page(self):
        self.client.login(username=self.username3, password=self.username3)
        response = self.client.get(self.url1, follow=True)
        self.assertEqual(response.status_code, 200)


    # Expected editor personal data is in the page
    def test_editor_page_has_editor_data(self):
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1, follow=True)
        content = response.content

        # This uses default data from EditorFactory.
        self.assertIn('alice', content)                 # wp_username
        self.assertIn('42', content)                    # edit count
        self.assertIn('some groups', content)           # wp_groups
        self.assertIn('some rights', content)           # wp_rights
        self.assertIn(WIKIS[0][0], content)             # home wiki
        self.assertIn('Cat floofing, telemetry, fermentation', content)


    # Expected editor application data is in the page
    def test_editor_page_has_application_history(self):
        app1 = ApplicationFactory(status=Application.PENDING, user=self.user1)
        app2 = ApplicationFactory(status=Application.QUESTION, user=self.user1)
        app3 = ApplicationFactory(status=Application.APPROVED, user=self.user1)
        app4 = ApplicationFactory(status=Application.NOT_APPROVED, user=self.user1)

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
