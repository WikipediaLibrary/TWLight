import random

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, Client

from .helpers.wiki_list import WIKIS
from .factories import EditorFactory

# Should be replaced with a proper factory, but factory-boy plus new migrations
# infrastructure doesn't seem to work right in tests.

todays_wiki = random.choice(WIKIS)[0]


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
            kwargs={'pk': self.user1.pk})


        # User 2: regular Editor
        self.username2 = 'bob'
        self.user2 = get_or_create_user(self.username2)
        self.editor2 = EditorFactory(user=self.user2)
        self.url2 = reverse('users:editor_detail',
            kwargs={'pk': self.user2.pk})


        # User 3: Site administrator
        self.username3 = 'carol'
        self.user3 = get_or_create_user(self.username3)
        self.user3.is_superuser = True
        self.user3.save()
        self.editor3 = EditorFactory(user=self.user3)


    def tearDown(self):
        self.user1.delete()
        self.editor1.delete()
        self.user2.delete()
        self.editor2.delete()
        self.user3.delete()
        self.editor3.delete()


    # EditorDetailView resolves at URL
    def test_editor_detail_url_resolves(self):
        """
        The EditorDetailView resolves.
        """
        found = resolve(self.url1)


    # Anonymous user cannot see editor page
    def test_anon_user_cannot_see_editor_details(self):
        response = self.client.get(self.url1)
        redirect_url = '{redirect_base}?next={next}'.format(
            redirect_base=settings.LOGIN_URL, next=self.url1)
        self.assertRedirects(response, redirect_url)


    # Editor can see own page
    def test_editor_can_see_own_page(self):
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1)
        self.assertEqual(response.status_code, 200)


    # Editor cannot see someone else's info
    def test_editor_cannot_see_other_editor_page(self):
        self.client.login(username=self.username1, password=self.username1)
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
        self.client.login(username=self.username3, password=self.username3)
        response = self.client.get(self.url1)
        self.assertEqual(response.status_code, 200)


    # Expected editor data is in the page
    def test_editor_page_has_data(self):
        self.client.login(username=self.username1, password=self.username1)
        response = self.client.get(self.url1)
        content = response.content
        self.assertIn('alice', content)     # wp_username
        self.assertIn('42', content)          # edit count
        self.assertIn('blah blah blah', content)          # wp_internal
        self.assertIn(todays_wiki, content) # home wiki
        self.assertIn('telecommunications project on the Latin wiki', content)

# Does django-braces give me a like can-see-own mixin? can I decorate that?

# Test user creation
# receiving signal from oauth results in creation of editor model
# site admin status is false
# editor model contains all expected info (mock out the signal)
