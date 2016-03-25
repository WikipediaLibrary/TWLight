from datetime import datetime
import random

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, Client

from .helpers.wiki_list import WIKIS
from .models import Editor
from .views import EditorDetailView

# Should be replaced with a proper factory, but factory-boy plus new migrations
# infrastructure doesn't seem to work right in tests.

todays_wiki = random.choice(WIKIS)[0]

def create_editor(user):
    editor = Editor()
    editor.user = user
    editor.wp_username = 'alice'
    editor.wp_editcount = 42
    editor.wp_registered = datetime.today()
    editor.wp_sub = '316758'
    editor._wp_internal = 'blah blah blah'
    editor.home_wiki = todays_wiki
    editor.contributions = 'telecommunications project on the Latin wiki'
    editor.email = 'alice@example.com'
    editor.save()
    return editor


class ViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        # User 1: regular Editor
        self.username1 = 'alice'
        self.user1, _ = User.objects.get_or_create(
            username=self.username1, password='password')
        self.editor1 = create_editor(self.user1)
        self.url1 = reverse('users:editor_detail',
            kwargs={'pk': self.editor1.pk})

        # User 2: regular Editor
        self.username2 = 'bob'
        self.user2, _ = User.objects.get_or_create(
            username=self.username2, password='password')
        self.editor2 = create_editor(self.user2)
        self.url2 = reverse('users:editor_detail',
            kwargs={'pk': self.editor2.pk})

        # User 3: Site administrator
        self.username3 = 'carol'
        self.user3, _ = User.objects.get_or_create(
            username=self.username3, password='password')
        self.user3.is_admin = True
        self.user3.save()
        self.editor3 = create_editor(self.user3)


    def tearDown(self):
        self.user1.delete()
        self.editor1.delete()


    # EditorDetailView resolves at URL
    def test_editor_detail_url_resolves(self):
        """
        The EditorDetailView resolves and uses the expected function.
        """
        found = resolve(self.url1)
        self.assertEqual(found.func.__code__,
            EditorDetailView.as_view().__code__)


    # Anonymous user cannot see editor page
    def test_anon_user_cannot_see_editor_details(self):
        response = self.client.get(self.url1)
        redirect_url = '{redirect_base}?next={next}'.format(
            redirect_base=settings.LOGIN_URL, next=self.url1)
        self.assertRedirects(response, redirect_url)


    # Editor can see own page
    def test_editor_can_see_own_page(self):
        self.client.login(username=self.username1, password='password')
        response = self.client.get(self.url1)
        self.assertEqual(response.status_code, 200)


    # Editor cannot see someone else's info
    def test_editor_cannot_see_other_editor_page(self):
        self.client.login(username=self.username1, password='password')
        response = self.client.get(self.url2)
        self.assertEqual(response.status_code, 403)


    # Coordinator can see someone else's info
    def test_coordinator_access(self):
        # This test needs to be written after we've ripped out the coordinator
        # class, so we're just using groups.
        # While you're at it, make sure user has a post-save hook to make
        # Editors exist.
        assert False


    # Site admin can see someone else's info
    def test_site_admin_can_see_other_editor_page(self):
        self.client.login(username=self.username3, password='password')
        response = self.client.get(self.url1)
        self.assertEqual(response.status_code, 200)

    # Expected editor data is in the page
    def test_editor_page_has_data(self):
        self.client.login(username=self.username1, password='password')
        response = self.client.get(self.url1)
        content = response.content
        self.assertIn('alice', content)     # wp_username
        self.assertIn(42, content)          # edit count
        self.assertIn('blah blah blah', content)          # wp_internal
        self.assertIn(todays_wiki, content) # home wiki
        self.assertIn('telecommunications project on the Latin wiki', content)

# Does django-braces give me a like can-see-own mixin? can I decorate that?

# Test user creation
# receiving signal from oauth results in creation of editor model
# site admin status is false
# editor model contains all expected info (mock out the signal)
