# -*- coding: utf-8 -*-
import copy
from datetime import datetime, date, timedelta
import json
import re
from unittest.mock import patch, Mock
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import resolve, reverse
from django.core.management import call_command
from django.test import TestCase, Client, RequestFactory
from django.utils.translation import get_language
from django.utils.html import escape
from django.utils.timezone import now
from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.factories import PartnerFactory
from TWLight.resources.models import Partner
from TWLight.resources.tests import EditorCraftRoom
from TWLight.users.models import Authorization

from . import views
from .authorization import OAuthBackend
from .helpers.wiki_list import WIKIS, LANGUAGE_CODES
from .factories import EditorFactory, UserFactory
from .groups import get_coordinators, get_restricted
from .models import (
    UserProfile,
    Editor,
    Authorization,
    editor_valid,
    editor_account_old_enough,
    editor_enough_edits,
    editor_not_blocked,
    editor_reg_date,
    editor_recent_edits,
    editor_bundle_eligible,
)

FAKE_IDENTITY_DATA = {"query": {"userinfo": {"options": {"disablemail": 0}}}}

FAKE_IDENTITY = {
    "editcount": 5000,
    "registered": "20151106154629",  # Well before first commit.
    "blocked": False,
    "iss": urlparse(settings.TWLIGHT_OAUTH_PROVIDER_URL).scheme
    + urlparse(settings.TWLIGHT_OAUTH_PROVIDER_URL).netloc,
    "sub": 567823,
    "rights": ["deletion", "spaceflight", "autoconfirmed"],
    "groups": ["charismatic megafauna"],
    "email": "alice@example.com",
    "username": "alice",
}

FAKE_GLOBAL_USERINFO = {
    "home": "enwiki",
    "id": 567823,
    "registration": "2015-11-06T15:46:29Z",  # Well before first commit.
    "name": "alice",
    "editcount": 5000,
}

# CSRF middleware is helpful for site security, but not helpful for testing
# the rendered output of a page.
def remove_csrfmiddlewaretoken(rendered_html):
    csrfmiddlewaretoken_pattern = (
        r"<input type='hidden' name='csrfmiddlewaretoken' value='.+' />"
    )
    return re.sub(csrfmiddlewaretoken_pattern, "", rendered_html)


class ViewsTestCase(TestCase):
    def setUp(self):
        super(ViewsTestCase, self).setUp()
        self.client = Client()

        # User 1: regular Editor
        self.username1 = "alice"
        self.user_editor = UserFactory(username=self.username1)
        self.editor1 = EditorFactory(user=self.user_editor)
        self.url1 = reverse("users:editor_detail", kwargs={"pk": self.editor1.pk})

        # User 2: regular Editor
        self.username2 = "bob"
        self.user_editor2 = UserFactory(username=self.username2)
        self.editor2 = EditorFactory(user=self.user_editor2)
        self.url2 = reverse("users:editor_detail", kwargs={"pk": self.editor2.pk})

        # User 3: Site administrator
        self.username3 = "carol"
        self.user_superuser = UserFactory(username=self.username3)
        self.user_superuser.is_superuser = True
        self.user_superuser.save()
        self.editor3 = EditorFactory(user=self.user_superuser)

        # User 4: Coordinator
        self.username4 = "eve"
        self.user_coordinator = UserFactory(username=self.username4)
        self.editor4 = EditorFactory(user=self.user_coordinator)
        get_coordinators().user_set.add(self.user_coordinator)

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        self.message_patcher = patch("TWLight.applications.views.messages.add_message")
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
        self.assertEqual(urlparse(response.url).path, settings.LOGIN_URL)

    def test_editor_can_see_own_page(self):
        """Check that editors can see their own pages."""
        factory = RequestFactory()
        request = factory.get(self.url1)
        request.user = self.user_editor

        response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)
        self.assertEqual(response.status_code, 200)

    def test_user_view_no_coordinators(self):
        """Check that users with no coordinators can see their own pages."""
        get_coordinators().user_set.remove(self.user_coordinator)
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

        # Define a partner
        partner = PartnerFactory()

        # Editor applies to the partner
        app = ApplicationFactory(
            status=Application.PENDING, editor=self.editor1, partner=partner
        )
        app.save()

        # Editor details should not be visible to just any coordinator
        try:
            response = views.EditorDetailView.as_view()(request, pk=self.editor1.pk)
            self.fail("Editor details should not be visible to just any coordinator.")
        except PermissionDenied:
            pass

        # Designate the coordinator
        partner.coordinator = request.user
        partner.save()

        # Editor details should be visible to the designated coordinator
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

        content = response.render().content.decode("utf-8")

        # This uses default data from EditorFactory, except for the username,
        # which is randomly generated (hence has no default).
        self.assertIn(self.editor1.wp_username, content)
        self.assertIn("42", content)
        self.assertIn("Cat floofing, telemetry, fermentation", content)

    def test_my_applications_page_has_application_history(self):
        """Expected editor application oauth_data is in their page."""
        app1 = ApplicationFactory(
            status=Application.PENDING, editor=self.user_editor.editor
        )
        app2 = ApplicationFactory(
            status=Application.QUESTION, editor=self.user_editor.editor
        )
        app3 = ApplicationFactory(
            status=Application.APPROVED, editor=self.user_editor.editor
        )
        app4 = ApplicationFactory(
            status=Application.NOT_APPROVED, editor=self.user_editor.editor
        )

        factory = RequestFactory()
        request = factory.get(
            reverse("users:my_applications", kwargs={"pk": self.editor1.pk})
        )
        request.user = self.user_editor

        response = views.ListApplicationsUserView.as_view()(request, pk=self.editor1.pk)

        self.assertEqual(
            set(response.context_data["object_list"]), {app1, app2, app3, app4}
        )
        content = response.render().content.decode("utf-8")

        self.assertIn(escape(app1.partner.company_name), content)
        self.assertIn(escape(app2.partner.company_name), content)
        self.assertIn(escape(app3.partner.company_name), content)
        self.assertIn(escape(app4.partner.company_name), content)

        # We can't use assertTemplateUsed with RequestFactory (only with
        # Client), and testing that the rendered content is equal to an
        # expected string is too fragile.

    def test_my_library_page_has_authorizations(self):
        partner1 = PartnerFactory(authorization_method=Partner.PROXY)
        ApplicationFactory(
            status=Application.PENDING, editor=self.user_editor.editor, partner=partner1
        )
        partner2 = PartnerFactory(authorization_method=Partner.BUNDLE)
        ApplicationFactory(
            status=Application.QUESTION,
            editor=self.user_editor.editor,
            partner=partner2,
        )
        partner3 = PartnerFactory(authorization_method=Partner.CODES)
        ApplicationFactory(
            status=Application.APPROVED,
            editor=self.user_editor.editor,
            partner=partner3,
        )
        partner4 = PartnerFactory(authorization_method=Partner.EMAIL)
        ApplicationFactory(
            status=Application.NOT_APPROVED,
            editor=self.user_editor.editor,
            partner=partner4,
        )
        partner5 = PartnerFactory(authorization_method=Partner.LINK)
        ApplicationFactory(
            status=Application.NOT_APPROVED,
            editor=self.user_editor.editor,
            partner=partner5,
        )

        factory = RequestFactory()
        request = factory.get(
            reverse("users:my_library", kwargs={"pk": self.editor1.pk})
        )
        request.user = self.user_editor

        response = views.CollectionUserView.as_view()(request, pk=self.editor1.pk)

        for each_authorization in response.context_data["proxy_bundle_authorizations"]:
            self.assertEqual(each_authorization.user, self.user_editor)
            self.assertTrue(
                each_authorization.partner == partner1
                or each_authorization.partner == partner2
            )

        for each_authorization in response.context_data["manual_authorizations"]:
            self.assertEqual(each_authorization.user, self.user_editor)
            self.assertTrue(
                each_authorization.partner == partner3
                or each_authorization.partner == partner4
                or each_authorization.partner == partner5
            )

    def test_return_authorization(self):
        # Simulate a valid user trying to return their access
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(authorization_method=Partner.PROXY)
        app = ApplicationFactory(
            status=Application.SENT, editor=editor, partner=partner
        )
        authorization = Authorization.objects.get(user=editor.user, partner=partner)
        self.assertEqual(authorization.get_latest_app(), app)
        return_url = reverse(
            "users:return_authorization", kwargs={"pk": authorization.pk}
        )
        response = self.client.get(return_url, follow=True)
        return_form = response.context["form"]
        self.client.post(return_url, return_form.initial)
        yesterday = datetime.now().date() - timedelta(days=1)
        authorization.refresh_from_db()
        self.assertEqual(authorization.date_expires, yesterday)

        # Simulate an invalid user trying to return access of some other user
        someday = yesterday + timedelta(days=30)
        authorization.date_expires = someday
        authorization.save()
        EditorCraftRoom(self, Terms=True, Coordinator=False)
        return_url = reverse(
            "users:return_authorization", kwargs={"pk": authorization.pk}
        )
        response = self.client.get(return_url, follow=True)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(return_url, return_form.initial)
        self.assertEqual(response.status_code, 403)
        authorization.refresh_from_db()
        self.assertEqual(authorization.date_expires, someday)

    def test_user_home_view_anon(self):
        """
        If an AnonymousUser hits UserHomeView, they are redirected to login.
        """
        factory = RequestFactory()
        request = factory.get(reverse("users:home"))
        request.user = AnonymousUser()

        response = views.UserHomeView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, settings.LOGIN_URL)

    def test_user_home_view_is_editor(self):
        """
        If a User who is an editor hits UserHomeView, they see EditorDetailView.
        """
        user = UserFactory()
        editor = EditorFactory(user=user)

        factory = RequestFactory()

        home_request = factory.get(reverse("users:home"))
        home_request.user = user
        home_response = views.UserHomeView.as_view()(home_request)

        detail_request = factory.get(
            reverse("users:editor_detail", kwargs={"pk": editor.pk})
        )
        detail_request.user = user
        detail_response = views.EditorDetailView.as_view()(detail_request, pk=editor.pk)

        # We can't actually check that EditorDetailView was used by UserHomeView
        # directly, because its as_view function has already been processed
        # and all we have access to is a return value. So let's check that the
        # output of the two pages is the same - the user would have seen the
        # same thing on either page.
        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(
            remove_csrfmiddlewaretoken(home_response.render().content.decode("utf-8")),
            remove_csrfmiddlewaretoken(
                detail_response.render().content.decode("utf-8")
            ),
        )

    @patch("TWLight.users.views.UserDetailView.as_view")
    def test_user_home_view_non_editor(self, mock_view):
        """
        A User who isn't an editor hitting UserHomeView sees UserDetailView.
        """
        user = UserFactory(username="not_an_editor")
        self.assertFalse(hasattr(user, "editor"))

        factory = RequestFactory()

        request = factory.get(reverse("users:home"))
        request.user = user
        _ = views.UserHomeView.as_view()(request)

        # For this we can't even check that the rendered content is the same,
        # because we don't have a URL allowing us to render UserDetailView
        # correctly; we'll mock out its as_view function and make sure it got
        # called.
        mock_view.assert_called_once_with()

    def test_coordinator_restricted(self):
        # If a coordinator restricts their data processing
        # they should stop being a coordinator.
        restrict_url = reverse("users:restrict_data")

        coordinators = get_coordinators()
        restricted = get_restricted()

        # Double check that the coordinator still has the relevant group
        assert self.user_coordinator in coordinators.user_set.all()

        # Need a password so we can login
        self.user_coordinator.set_password("editor")
        self.user_coordinator.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username4, password="editor")
        restrict = self.client.get(restrict_url, follow=True)
        restrict_form = restrict.context["form"]
        data = restrict_form.initial
        data["restricted"] = True
        data["submit"] = True
        agree = self.client.post(restrict_url, data)

        assert self.user_coordinator not in coordinators.user_set.all()
        assert self.user_coordinator in restricted.user_set.all()

    def test_user_delete(self):
        """
        Verify that deleted users have no user object.
        """
        delete_url = reverse("users:delete_data", kwargs={"pk": self.user_editor.pk})

        # Need a password so we can login
        self.user_editor.set_password("editor")
        self.user_editor.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username1, password="editor")

        submit = self.client.post(delete_url)

        assert not User.objects.filter(username=self.username1).exists()
        # Check that the associated Editor also got deleted.
        assert not Editor.objects.filter(user=self.user_editor).exists()

    def test_user_delete_authorizations(self):
        """
        Verify that deleted user authorizations are expired and contain no user links
        """
        delete_url = reverse("users:delete_data", kwargs={"pk": self.user_editor.pk})

        # Need a password so we can login
        self.user_editor.set_password("editor")
        self.user_editor.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username1, password="editor")

        partner = PartnerFactory()
        user_auth = Authorization(
            user=self.user_editor,
            partner=partner,
            date_authorized=date.today(),
            date_expires=date.today() + timedelta(days=30),
        )
        user_auth.save()

        submit = self.client.post(delete_url)

        user_auth.refresh_from_db()
        self.assertEqual(user_auth.date_expires, date.today() - timedelta(days=1))

    def test_user_data_download(self):
        """
        Verify that if users try to download their personal data they
        are actually sent a file.
        """
        # Need a password so we can login
        self.user_editor2.set_password("editor")
        self.user_editor2.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username2, password="editor")

        response = self.client.post(self.url2, {"download": "Download"})

        self.assertEqual(
            response.get("Content-Disposition"), "attachment; filename=user_data.json"
        )

    def test_user_email_form(self):
        """
        Users have a form available on their user pages which enables them to
        control which emails they receive. Verify that they can post this form
        without error.
        """
        # Need a password so we can login
        self.user_editor2.set_password("editor")
        self.user_editor2.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username2, password="editor")

        response = self.client.post(self.url2, {"update_email_settings": ["Update"]})

        # Should be successfully redirected back to the user page.
        self.assertEqual(response.status_code, 302)

    def test_user_email_preferences_disable_update(self):
        """
        Verify that users can disable renewal notices and coordinator reminder
        emails in the email form.
        """
        # Need a password so we can login
        self.user_editor2.set_password("editor")
        self.user_editor2.save()
        # Only coordinators get to change their reminder preferences
        get_coordinators().user_set.add(self.user_editor2)

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username2, password="editor")

        response = self.client.post(self.url2, {"update_email_settings": ["Update"]})

        # Should be successfully redirected back to the user page.
        self.assertEqual(response.status_code, 302)

        self.user_editor2.userprofile.refresh_from_db()

        # We didn't send send_renewal_notices or send_pending_application_reminders
        # or send_discussion_application_reminders or send_approved_application_reminders
        # in POST to simulate an unchecked box.
        self.assertEqual(self.user_editor2.userprofile.send_renewal_notices, False)
        self.assertEqual(self.user_editor2.userprofile.pending_app_reminders, False)
        self.assertEqual(self.user_editor2.userprofile.discussion_app_reminders, False)
        self.assertEqual(self.user_editor2.userprofile.approved_app_reminders, False)

    def test_user_email_preferences_enable_update(self):
        """
        Verify that users can email renewal notices and coordinator reminder
        emails in the email form.
        """
        # Need a password so we can login
        self.user_editor2.set_password("editor")
        self.user_editor2.userprofile.send_renewal_notices = False
        self.user_editor2.userprofile.pending_app_reminders = False
        self.user_editor2.userprofile.discussion_app_reminders = False
        self.user_editor2.userprofile.approved_app_reminders = False
        self.user_editor2.save()
        # Only coordinators get to change their reminder preferences
        get_coordinators().user_set.add(self.user_editor2)

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username2, password="editor")

        response = self.client.post(
            self.url2,
            {
                "update_email_settings": ["Update"],
                "send_renewal_notices": ["on"],
                "send_pending_application_reminders": ["on"],
                "send_discussion_application_reminders": ["on"],
                "send_approved_application_reminders": ["on"],
            },
        )

        # Should be successfully redirected back to the user page.
        self.assertEqual(response.status_code, 302)

        self.user_editor2.userprofile.refresh_from_db()

        self.assertEqual(self.user_editor2.userprofile.send_renewal_notices, True)
        self.assertEqual(self.user_editor2.userprofile.pending_app_reminders, True)
        self.assertEqual(self.user_editor2.userprofile.discussion_app_reminders, True)
        self.assertEqual(self.user_editor2.userprofile.approved_app_reminders, True)

    def test_user_email_preferences_update_non_coordinator(self):
        # Need a password so we can login
        self.user_editor2.set_password("editor")
        self.user_editor2.userprofile.send_renewal_notices = False
        self.user_editor2.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username2, password="editor")

        response = self.client.post(
            self.url2,
            {"update_email_settings": ["Update"], "send_renewal_notices": ["on"]},
        )

        # Should be successfully redirected back to the user page.
        self.assertEqual(response.status_code, 302)

        self.user_editor2.userprofile.refresh_from_db()

        self.assertEqual(self.user_editor2.userprofile.send_renewal_notices, True)
        # Only coordinators get to change their reminder preferences
        self.assertEqual(self.user_editor2.userprofile.pending_app_reminders, True)
        self.assertEqual(self.user_editor2.userprofile.discussion_app_reminders, True)
        self.assertEqual(self.user_editor2.userprofile.approved_app_reminders, True)


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
        user = User.objects.create_user(
            username="profiler", email="profiler@example.com"
        )
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.terms_of_use, False)

        user.delete()

    def test_user_profile_sets_use_wp_email_to_true(self):
        """
        Verify that UserProfile.use_wp_email defaults to True.
        (Editor.update_from_wikipedia assumes this to be the case.)
        """
        user = User.objects.create_user(
            username="profiler", email="profiler@example.com"
        )
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
        self.test_editor = EditorFactory(
            wp_username="editor_model_test",
            wp_rights=json.dumps(["cat floofing", "the big red button"]),
            wp_groups=json.dumps(["sysops", "bureaucrats"]),
        )

    def tearDown(self):
        super(EditorModelTestCase, self).tearDown()
        self.test_editor.delete()

    def test_encoder_works_with_special_character_username(self):
        test = Editor().encode_wp_username("editor model&test")
        self.assertEqual(test, "editor%20model%26test")

    def test_wp_user_page_url(self):
        expected_url = settings.TWLIGHT_OAUTH_PROVIDER_URL + "/User:editor_model_test"
        self.assertEqual(expected_url, self.test_editor.wp_user_page_url)

    def test_wp_link_central_auth(self):
        expected_url = "https://meta.wikimedia.org/w/index.php?title=Special%3ACentralAuth&target=editor_model_test"
        self.assertEqual(expected_url, self.test_editor.wp_link_central_auth)

    def test_get_wp_rights_display(self):
        expected_text = ["cat floofing", "the big red button"]
        self.assertEqual(expected_text, self.test_editor.get_wp_rights_display)

    def test_get_wp_groups_display(self):
        expected_text = ["sysops", "bureaucrats"]
        self.assertEqual(expected_text, self.test_editor.get_wp_groups_display)

    def test_is_user_valid(self):
        """
        Users must:
        * Have >= 500 edits
        * Be active for >= 6 months
        * Have Special:Email User enabled
        * Not be blocked on any projects
        """

        identity = copy.copy(FAKE_IDENTITY)
        global_userinfo = copy.copy(FAKE_GLOBAL_USERINFO)

        # Valid data
        global_userinfo["editcount"] = 500
        self.test_editor.wp_editcount = 500
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        enough_edits = editor_enough_edits(global_userinfo)
        not_blocked = editor_not_blocked(identity)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertTrue(valid)

        # Edge case
        global_userinfo["editcount"] = 500
        enough_edits = editor_enough_edits(global_userinfo)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertTrue(valid)

        # Too few edits
        global_userinfo["editcount"] = 499
        enough_edits = editor_enough_edits(global_userinfo)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertFalse(valid)

        # Account created too recently
        global_userinfo["editcount"] = 500
        identity["registered"] = datetime.today().strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        enough_edits = editor_enough_edits(global_userinfo)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertFalse(valid)

        # Edge case: this shouldn't.
        almost_6_months_ago = datetime.today() - timedelta(days=183)
        identity["registered"] = almost_6_months_ago.strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertTrue(valid)

        # Edge case: this should work.
        almost_6_months_ago = datetime.today() - timedelta(days=182)
        identity["registered"] = almost_6_months_ago.strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertTrue(valid)

        # Bad editor! No biscuit.
        identity["blocked"] = True
        not_blocked = editor_not_blocked(identity)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertFalse(valid)

    def test_editor_eligibility_functions(self):
        # Start out with basic validation of the eligibility functions.

        # Invalid users without enough recent edits are not eligible.
        self.assertFalse(editor_bundle_eligible(False, False))

        # Invalid users with enough recent edits are not eligible.
        self.assertFalse(editor_bundle_eligible(False, True))

        # Valid users without enough recent edits are not eligible.
        self.assertFalse(editor_bundle_eligible(True, False))

        # Valid users with enough recent edits are eligible.
        self.assertTrue(editor_bundle_eligible(True, True))

    def test_is_user_bundle_eligible(self):
        """
        Users must:
        * Be valid
        * Have made 10 edits in the last 30 days (with some wiggle room, as you will see)
        """

        identity = copy.copy(FAKE_IDENTITY)
        global_userinfo = copy.copy(FAKE_GLOBAL_USERINFO)

        # Valid data
        global_userinfo["editcount"] = 500
        self.test_editor.wp_editcount = 500
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        enough_edits = editor_enough_edits(global_userinfo)
        not_blocked = editor_not_blocked(identity)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.assertTrue(valid)

        # 1st time bundle check should always pass for a valid user.
        self.test_editor.wp_editcount_prev_updated, self.test_editor.wp_editcount_prev, self.test_editor.wp_editcount_recent, self.test_editor.wp_enough_recent_edits = editor_recent_edits(
            global_userinfo["editcount"],
            None,
            self.test_editor.wp_editcount,
            None,
            self.test_editor.wp_editcount_prev,
            self.test_editor.wp_editcount_recent,
            self.test_editor.wp_enough_recent_edits,
        )
        bundle_eligible = editor_bundle_eligible(
            valid, self.test_editor.wp_enough_recent_edits
        )
        self.assertTrue(bundle_eligible)

        # A valid user should pass 30 days after their first login, even if they haven't made anymore edits.
        self.test_editor.wp_editcount_updated = now() - timedelta(days=30)
        self.test_editor.wp_editcount_prev_updated = (
            self.test_editor.wp_editcount_prev_updated - timedelta(days=30)
        )
        self.test_editor.wp_editcount_prev_updated, self.test_editor.wp_editcount_prev, self.test_editor.wp_editcount_recent, self.test_editor.wp_enough_recent_edits = editor_recent_edits(
            global_userinfo["editcount"],
            self.test_editor.wp_editcount_updated,
            self.test_editor.wp_editcount,
            self.test_editor.wp_editcount_prev_updated,
            self.test_editor.wp_editcount_prev,
            self.test_editor.wp_editcount_recent,
            self.test_editor.wp_enough_recent_edits,
        )
        bundle_eligible = editor_bundle_eligible(
            valid, self.test_editor.wp_enough_recent_edits
        )
        self.assertTrue(bundle_eligible)

        # A valid user should fail 31 days after their first login, if they haven't made any more edits.
        self.test_editor.wp_editcount_updated = now() - timedelta(days=31)
        self.test_editor.wp_editcount_prev_updated = (
            self.test_editor.wp_editcount_prev_updated - timedelta(days=31)
        )
        self.test_editor.wp_editcount_prev_updated, self.test_editor.wp_editcount_prev, self.test_editor.wp_editcount_recent, self.test_editor.wp_enough_recent_edits = editor_recent_edits(
            global_userinfo["editcount"],
            self.test_editor.wp_editcount_updated,
            self.test_editor.wp_editcount,
            self.test_editor.wp_editcount_prev_updated,
            self.test_editor.wp_editcount_prev,
            self.test_editor.wp_editcount_recent,
            self.test_editor.wp_enough_recent_edits,
        )
        bundle_eligible = editor_bundle_eligible(
            valid, self.test_editor.wp_enough_recent_edits
        )
        self.assertFalse(bundle_eligible)

        # A valid user should pass 31 days after their first login if they have made enough edits.
        self.test_editor.wp_editcount_prev_updated, self.test_editor.wp_editcount_prev, self.test_editor.wp_editcount_recent, self.test_editor.wp_enough_recent_edits = editor_recent_edits(
            global_userinfo["editcount"] + 10,
            self.test_editor.wp_editcount_updated,
            self.test_editor.wp_editcount,
            self.test_editor.wp_editcount_prev_updated,
            self.test_editor.wp_editcount_prev,
            self.test_editor.wp_editcount_recent,
            self.test_editor.wp_enough_recent_edits,
        )
        bundle_eligible = editor_bundle_eligible(
            valid, self.test_editor.wp_enough_recent_edits
        )
        self.test_editor.wp_editcount_updated = now()
        self.assertTrue(bundle_eligible)

        # Bad editor! No biscuit, even if you have enough edits.
        identity["blocked"] = True
        not_blocked = editor_not_blocked(identity)
        valid = editor_valid(enough_edits, account_old_enough, not_blocked)
        self.test_editor.wp_editcount_updated = now() - timedelta(days=31)
        self.test_editor.wp_editcount_prev_updated = (
            self.test_editor.wp_editcount_prev_updated - timedelta(days=31)
        )
        self.test_editor.wp_editcount_prev_updated, self.test_editor.wp_editcount_prev, self.test_editor.wp_editcount_recent, self.test_editor.wp_enough_recent_edits = editor_recent_edits(
            global_userinfo["editcount"] + 10,
            self.test_editor.wp_editcount_updated,
            self.test_editor.wp_editcount,
            self.test_editor.wp_editcount_prev_updated,
            self.test_editor.wp_editcount_prev,
            self.test_editor.wp_editcount_recent,
            self.test_editor.wp_enough_recent_edits,
        )
        bundle_eligible = editor_bundle_eligible(
            valid, self.test_editor.wp_enough_recent_edits
        )
        self.test_editor.wp_editcount_updated = now()
        self.assertFalse(bundle_eligible)

        # Without a scheduled management command, a valid user will pass 60 days after their first login if they have 10 more edits,
        # even if we're not sure whether they made those edits in the last 30 days.

        # Valid data for first time logging in after bundle was launched. 60 days ago.
        global_userinfo["editcount"] = 500
        identity["blocked"] = False
        self.test_editor.wp_editcount = global_userinfo["editcount"]
        self.test_editor.wp_registered = editor_reg_date(identity, global_userinfo)
        self.test_editor.wp_account_old_enough = editor_account_old_enough(registered)
        self.test_editor.wp_enough_edits = editor_enough_edits(global_userinfo)
        self.test_editor.wp_not_blocked = editor_not_blocked(identity)
        self.test_editor.wp_valid = editor_valid(
            self.test_editor.wp_enough_edits,
            self.test_editor.wp_account_old_enough,
            self.test_editor.wp_not_blocked,
        )
        self.test_editor.wp_editcount_updated = now() - timedelta(days=60)
        self.test_editor.wp_editcount_prev_updated = (
            self.test_editor.wp_editcount_prev_updated - timedelta(days=60)
        )
        self.test_editor.wp_bundle_eligible = True
        self.test_editor.save()

        # 15 days later, they logged with 10 more edits. Valid
        global_userinfo["editcount"] = global_userinfo["editcount"] + 10
        self.test_editor.wp_editcount = global_userinfo["editcount"]
        self.test_editor.wp_editcount_updated = (
            self.test_editor.wp_editcount_updated + timedelta(days=15)
        )
        self.test_editor.wp_editcount_prev_updated = (
            self.test_editor.wp_editcount_prev_updated + timedelta(days=15)
        )
        self.test_editor.wp_bundle_eligible = True
        self.test_editor.save()
        self.test_editor.refresh_from_db()
        self.assertTrue(self.test_editor.wp_bundle_eligible)

        # 31 days later with no activity, their eligibility gets updated by the cron task.
        command = call_command(
            "user_update_eligibility",
            datetime=datetime.isoformat(
                self.test_editor.wp_editcount_updated + timedelta(days=31)
            ),
            global_userinfo=global_userinfo,
        )

        # They login today and aren't eligible for the bundle.
        self.test_editor.refresh_from_db()
        self.test_editor.wp_editcount_prev_updated, self.test_editor.wp_editcount_prev, self.test_editor.wp_editcount_recent, self.test_editor.wp_enough_recent_edits = editor_recent_edits(
            self.test_editor.wp_editcount,
            self.test_editor.wp_editcount_updated,
            self.test_editor.wp_editcount,
            self.test_editor.wp_editcount_prev_updated,
            self.test_editor.wp_editcount_prev,
            self.test_editor.wp_editcount_recent,
            self.test_editor.wp_enough_recent_edits,
        )
        self.test_editor.wp_bundle_eligible = editor_bundle_eligible(
            self.test_editor.wp_valid, self.test_editor.wp_enough_recent_edits
        )
        self.test_editor.save()
        self.assertFalse(self.test_editor.wp_bundle_eligible)

    @patch.object(Editor, "get_global_userinfo")
    def test_update_from_wikipedia(self, mock_global_userinfo):
        identity = {}
        identity["username"] = "evil_dr_porkchop"
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity["sub"] = self.test_editor.wp_sub
        identity["rights"] = ["deletion", "spaceflight"]
        identity["groups"] = ["charismatic megafauna"]
        # We should now be ignoring the oauth editcount
        identity["editcount"] = 42
        identity["email"] = "porkchop@example.com"
        identity["iss"] = "zh-classical.wikipedia.org"
        identity["registered"] = "20130205230142"
        # validity
        identity["blocked"] = False

        global_userinfo = {}
        global_userinfo["home"] = "zh_classicalwiki"
        global_userinfo["id"] = identity["sub"]
        global_userinfo["registration"] = "2013-02-05T23:01:42Z"
        global_userinfo["name"] = identity["username"]
        # We should now be using the global_userinfo editcount
        global_userinfo["editcount"] = 960

        # update_from_wikipedia calls get_global_userinfo, which generates an
        # API call to Wikipedia that we don't actually want to do in testing.
        mock_global_userinfo.return_value = global_userinfo

        # Don't change self.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory()
        new_identity = dict(identity)
        new_identity["sub"] = new_editor.wp_sub

        lang = get_language()
        new_editor.update_from_wikipedia(
            new_identity, lang
        )  # This call also saves the editor

        self.assertEqual(new_editor.wp_username, "evil_dr_porkchop")
        self.assertEqual(new_editor.wp_rights, json.dumps(["deletion", "spaceflight"]))
        self.assertEqual(new_editor.wp_groups, json.dumps(["charismatic megafauna"]))
        self.assertEqual(new_editor.wp_editcount, 960)
        self.assertEqual(new_editor.user.email, "porkchop@example.com")
        self.assertEqual(new_editor.wp_registered, datetime(2013, 2, 5).date())

        # Now check what happens if their wikipedia ID number has changed - this
        # should throw an error as we can no longer verify they're the same
        # editor.
        with self.assertRaises(AssertionError):
            new_identity["sub"] = new_editor.wp_sub + 1
            new_editor.update_from_wikipedia(
                new_identity, lang
            )  # This call also saves the editor


class OAuthTestCase(TestCase):
    def setUp(self):
        super(OAuthTestCase, self).setUp()
        # Prevent failures due to side effects from database artifacts.
        for editor in Editor.objects.all():
            editor.delete()

    @patch("urllib.request.urlopen")
    def test_create_user_and_editor(self, mock_urlopen):
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
        mock_urlopen.return_value = mock_response

        user, editor = oauth_backend._create_user_and_editor(identity)

        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.username, "567823")
        self.assertFalse(user.has_usable_password())

        self.assertEqual(editor.user, user)
        self.assertEqual(editor.wp_sub, 567823)
        # We won't test the fields set by update_from_wikipedia, as they are
        # tested elsewhere.

    # We mock out this function for two reasons:
    # 1) To prevent its call to an external API, which we would have otherwise
    #    had to mock anyway;
    # 2) So we can assert that it was called.
    @patch("TWLight.users.models.Editor.update_from_wikipedia")
    def test_get_and_update_user_from_identity_existing_user(self, mock_update):
        """
        OAuthBackend._get_and_update_user_from_identity() should:
        * If there is an Editor whose wp_sub = identity['sub']:
            * Return the user FKed onto that
            * Return created = False
        * Call Editor.update_from_wikipedia
        """
        # Make sure the test user has the username and language anticipated by our backend.
        username = FAKE_IDENTITY["sub"]
        lang = get_language()
        existing_user = UserFactory(username=username)
        params = {"user": existing_user, "wp_sub": FAKE_IDENTITY["sub"]}

        _ = EditorFactory(**params)

        oauth_backend = OAuthBackend()
        user, created = oauth_backend._get_and_update_user_from_identity(FAKE_IDENTITY)

        self.assertFalse(created)
        self.assertTrue(hasattr(user, "editor"))
        self.assertEqual(user, existing_user)

        mock_update.assert_called_once_with(FAKE_IDENTITY, lang)

    @patch("TWLight.users.models.Editor.update_from_wikipedia")
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
        identity["sub"] = new_sub
        self.assertFalse(Editor.objects.filter(wp_sub=new_sub).count())

        user, created = oauth_backend._get_and_update_user_from_identity(identity)

        self.assertTrue(created)
        self.assertTrue(hasattr(user, "editor"))
        self.assertEqual(user.editor.wp_sub, new_sub)

        mock_update.assert_called_once_with(identity, lang)


class TermsTestCase(TestCase):
    def test_terms_page_displays(self):
        """
        Terms page should display for authenticated users.

        We had a bug where attempting to view the page caused a 500 error.
        """
        _ = User.objects.create_user(username="termstestcase", password="bar")
        url = reverse("terms")

        c = Client()
        c.login(username="termstestcase", password="bar")
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
