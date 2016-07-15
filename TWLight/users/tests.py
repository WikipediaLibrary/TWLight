# -*- coding: utf-8 -*-
from urlparse import urlparse

from django.core.urlresolvers import resolve, reverse
from django.template.loader import render_to_string
from django.test import TestCase, Client, RequestFactory

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application

from . import views
from .helpers.wiki_list import WIKIS
from .factories import EditorFactory, UserFactory
from .groups import get_coordinators


class ViewsTestCase(TestCase):

    def setUp(self):
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


    def tearDown(self):
        self.user_editor.delete()
        self.editor1.delete()
        self.user_editor2.delete()
        self.editor2.delete()
        self.user_superuser.delete()
        self.editor3.delete()
        self.user_coordinator.delete()
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
        self.assertIn('wp_alice', content)                 # wp_username
        self.assertContains(response, '42')             # edit count
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


# TODO write these tests after design review
# Test user creation
# receiving signal from oauth results in creation of editor model
# site admin status is false
# editor model contains all expected info (mock out the signal)

# Terms of use
# After login they should be redirected to agreement page if not agreed
# Likewise for request-for-application
# Also for the application page itself
