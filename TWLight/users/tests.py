# -*- coding: utf-8 -*-
import copy
from datetime import datetime, date, timedelta
import json
import re
from unittest.mock import patch, Mock
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User, AnonymousUser
from django.core import mail
from django.core.exceptions import (
    PermissionDenied,
    SuspiciousOperation,
    ValidationError,
)
from django.urls import resolve, reverse
from django.core.management import call_command
from django.test import TestCase, Client, RequestFactory
from django.utils.translation import get_language
from django.utils.html import escape
from django.utils.timezone import now
from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.factories import PartnerFactory
from TWLight.resources.filters import INSTANT, MULTI_STEP
from TWLight.resources.models import Partner
from TWLight.resources.tests import EditorCraftRoom

from . import views
from .oauth import OAuthBackend
from .helpers.validation import validate_partners
from .helpers.authorizations import get_all_bundle_authorizations
from .helpers.wiki_list import WIKIS, LANGUAGE_CODES
from .factories import EditorFactory, UserFactory
from .groups import get_coordinators, get_restricted
from .models import UserProfile, Editor, Authorization
from .views import MyLibraryView

from TWLight.users.helpers.editor_data import (
    editor_valid,
    editor_account_old_enough,
    editor_enough_edits,
    editor_not_blocked,
    editor_reg_date,
    editor_bundle_eligible,
    editor_make_block_dict,
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

FAKE_MERGED_ACCOUNTS = [
    {
        "wiki": "enwiki",
        "url": "https://en.wikipedia.org",
        "timestamp": "2015-11-06T15:46:29Z",
        "method": "login",
        "editcount": 100,
        "registration": "2015-11-06T15:46:29Z",
        "groups": ["extendedconfirmed"],
    }
]

FAKE_MERGED_ACCOUNTS_BLOCKED = [
    {
        "wiki": "enwiki",
        "url": "https://en.wikipedia.org",
        "timestamp": "2015-11-06T15:46:29Z",
        "method": "login",
        "editcount": 100,
        "registration": "2015-11-06T15:46:29Z",
        "groups": ["extendedconfirmed"],
        "blocked": {"expiry": "infinity", "reason": "bad editor!"},
    }
]

FAKE_GLOBAL_USERINFO = {
    "home": "enwiki",
    "id": 567823,
    "registration": "2015-11-06T15:46:29Z",  # Well before first commit.
    "name": "alice",
    "editcount": 5000,
    "merged": copy.copy(FAKE_MERGED_ACCOUNTS),
}


# CSRF middleware is helpful for site security, but not helpful for testing
# the rendered output of a page.
def remove_csrfmiddlewaretoken(rendered_html):
    csrfmiddlewaretoken_pattern = (
        r"<input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\".+\">"
    )
    return re.sub(csrfmiddlewaretoken_pattern, "", rendered_html)


class ViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.client = Client()

        # User 1: regular Editor
        cls.username1 = "alice"
        cls.user_editor = UserFactory(username=cls.username1)
        cls.editor1 = EditorFactory(user=cls.user_editor)
        cls.editor1.wp_bundle_eligible = True
        cls.editor1.save()
        cls.url1 = reverse("users:editor_detail", kwargs={"pk": cls.editor1.pk})

        # User 2: regular Editor
        cls.username2 = "bob"
        cls.user_editor2 = UserFactory(username=cls.username2)
        cls.editor2 = EditorFactory(user=cls.user_editor2)
        cls.url2 = reverse("users:editor_detail", kwargs={"pk": cls.editor2.pk})

        # User 3: Site administrator
        cls.username3 = "carol"
        cls.user_superuser = UserFactory(username=cls.username3)
        cls.user_superuser.is_superuser = True
        cls.user_superuser.save()
        cls.editor3 = EditorFactory(user=cls.user_superuser)

        # User 4: Coordinator
        cls.username4 = "eve"
        cls.user_coordinator = UserFactory(username=cls.username4)
        cls.editor4 = EditorFactory(user=cls.user_coordinator)
        get_coordinators().user_set.add(cls.user_coordinator)

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.user_editor.delete()
        cls.editor1.delete()
        cls.user_editor2.delete()
        cls.editor2.delete()
        cls.user_superuser.delete()
        cls.editor3.delete()
        cls.user_coordinator.delete()
        cls.editor4.delete()
        cls.message_patcher.stop()

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
        # Bundle applications shouldn't be listed on this page
        app5 = ApplicationFactory(
            status=Application.APPROVED,
            partner=PartnerFactory(authorization_method=Partner.BUNDLE),
            editor=self.user_editor.editor,
        )
        app6 = ApplicationFactory(
            status=Application.PENDING,
            partner=PartnerFactory(authorization_method=Partner.BUNDLE),
            editor=self.user_editor.editor,
        )
        app7 = ApplicationFactory(
            status=Application.INVALID,
            partner=PartnerFactory(authorization_method=Partner.BUNDLE),
            editor=self.user_editor.editor,
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
        # No Bundle applications
        self.assertNotIn(escape(app5.partner.company_name), content)
        self.assertNotIn(escape(app6.partner.company_name), content)
        self.assertNotIn(escape(app7.partner.company_name), content)

        # We can't use assertTemplateUsed with RequestFactory (only with
        # Client), and testing that the rendered content is equal to an
        # expected string is too fragile.

    def test_withdraw_application(self):
        app = ApplicationFactory(
            status=Application.PENDING,
            partner=PartnerFactory(authorization_method=Partner.BUNDLE),
            editor=self.user_editor.editor,
        )

        factory = RequestFactory()
        request = factory.get(
            reverse("users:withdraw", kwargs={"pk": self.editor1.pk, "id": app.pk})
        )
        request.user = self.user_editor
        response = views.WithdrawApplication.as_view()(
            request, pk=self.editor1.pk, id=app.pk
        )
        app.refresh_from_db()
        # withdrawing application should set date closed
        self.assertNotEqual(app.date_closed, None)
        self.assertEqual(app.status, Application.INVALID)

    def test_sent_application(self):
        app = ApplicationFactory(
            status=Application.SENT,
            partner=PartnerFactory(authorization_method=Partner.BUNDLE),
            editor=self.user_editor.editor,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        request = factory.get(
            reverse("users:my_applications", kwargs={"pk": self.editor1.pk})
        )
        request.user = self.user_editor
        response = views.ListApplicationsUserView.as_view()(
            request,
            pk=self.editor1.pk,
        )
        app.refresh_from_db()
        self.assertNotIn("Withdraw", response.render().content.decode("utf-8"))

    def test_return_authorization(self):
        # Simulate a valid user trying to return their access
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(authorization_method=Partner.PROXY)
        app = ApplicationFactory(
            status=Application.SENT,
            editor=editor,
            partner=partner,
            sent_by=self.user_coordinator,
        )
        authorization = Authorization.objects.get(user=editor.user, partners=partner)
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

    def test_latest_application(self):
        # Create an editor with a session.
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)

        partner = PartnerFactory(authorization_method=Partner.PROXY)

        app = ApplicationFactory(
            status=Application.SENT,
            editor=editor,
            partner=partner,
            sent_by=self.user_coordinator,
        )
        authorization = Authorization.objects.get(user=editor.user, partners=partner)
        self.assertEqual(authorization.get_latest_app(), app)

        # Simulate a valid user trying to return their access
        return_url = reverse(
            "users:return_authorization", kwargs={"pk": authorization.pk}
        )
        response = self.client.get(return_url, follow=True)
        return_form = response.context["form"]
        self.client.post(return_url, return_form.initial)
        yesterday = datetime.now().date() - timedelta(days=1)
        authorization.refresh_from_db()
        self.assertEqual(authorization.date_expires, yesterday)

        # Create a new application to the same partner (in reality this
        # is most likely to be a renewal)
        app_renewal = ApplicationFactory(
            status=Application.SENT,
            editor=editor,
            partner=partner,
            sent_by=self.user_coordinator,
        )
        app_renewal.save()

        # return access
        authorization.refresh_from_db()
        return_url = reverse(
            "users:return_authorization", kwargs={"pk": authorization.pk}
        )
        response = self.client.get(return_url, follow=True)
        return_form = response.context["form"]
        self.client.post(return_url, return_form.initial)
        yesterday = datetime.now().date() - timedelta(days=1)
        authorization.refresh_from_db()
        self.assertEqual(authorization.date_expires, yesterday)

        # Renew again, but deny this time.
        app_renewal2 = ApplicationFactory(editor=editor, partner=partner)
        app_renewal2.status = Application.NOT_APPROVED
        app_renewal2.save()
        authorization.refresh_from_db()

        self.assertEqual(authorization.get_latest_app(), app_renewal)
        self.assertEqual(authorization.get_latest_sent_app(), app_renewal)

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
        TODO: Change this test's assertions (they might break when the csrf
        token is rendered differently)
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
        expected_detail_view = remove_csrfmiddlewaretoken(
            detail_response.rendered_content
        )
        home_view = remove_csrfmiddlewaretoken(home_response.rendered_content)
        self.assertEqual(expected_detail_view, home_view)

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
            authorizer=self.user_coordinator,
            date_authorized=date.today(),
            date_expires=date.today() + timedelta(days=30),
        )
        user_auth.save()
        user_auth.partners.add(partner)

        submit = self.client.post(delete_url)

        user_auth.refresh_from_db()
        self.assertEqual(user_auth.date_expires, date.today() - timedelta(days=1))

    def test_user_delete_bundle_authorizations(self):
        """
        Verify that deleted user authorizations are expired and contain no user links
        """
        delete_url = reverse("users:delete_data", kwargs={"pk": self.user_editor.pk})

        # Need a password so we can login
        self.editor1.user.set_password("editor")
        self.editor1.user.save()

        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.username1, password="editor")

        # Bundle authorization should be created
        self.editor1.update_bundle_authorization()

        self.editor1.refresh_from_db()

        bundle_auth = self.editor1.get_bundle_authorization

        self.assertTrue(bundle_auth.is_bundle)

        # Saving the bundle authorization id so we can query it after to make
        # sure it's been deleted
        bundle_auth_id = bundle_auth.pk

        submit = self.client.post(delete_url)

        editor_count = Editor.objects.filter(pk=self.editor1.pk).count()
        self.assertEqual(editor_count, 0)

        bundle_auth_count = Authorization.objects.filter(pk=bundle_auth_id).count()
        self.assertEqual(bundle_auth_count, 0)

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

    def test_terms_of_use_on_editor_detail_page_show(self):
        """Editor who agreed term of use, can see checkbox to disagree"""
        user_agreed_TOU = UserFactory()
        user_agreed_TOU.userprofile.terms_of_use = True
        editor_agreed_TOU = EditorFactory(user=user_agreed_TOU)
        factory = RequestFactory()
        detail_request = factory.get(
            reverse("users:editor_detail", kwargs={"pk": editor_agreed_TOU.pk})
        )
        detail_request.user = user_agreed_TOU
        response = views.EditorDetailView.as_view()(
            detail_request, pk=editor_agreed_TOU.pk
        )

        content = response.render().content.decode("utf-8")
        self.assertIn("By unchecking this box and clicking “Update", content)

    def test_terms_of_use_on_editor_detail_page_not_show(self):
        """Editor who hasn't agreed term of use, won't see checkbox to disagree"""
        user_not_agreed_TOU = UserFactory()
        user_not_agreed_TOU.userprofile.terms_of_use = False
        editor_not_agreed_TOU = EditorFactory(user=user_not_agreed_TOU)
        factory = RequestFactory()
        detail_request = factory.get(
            reverse("users:editor_detail", kwargs={"pk": editor_not_agreed_TOU.pk})
        )
        detail_request.user = user_not_agreed_TOU
        response = views.EditorDetailView.as_view()(
            detail_request, pk=editor_not_agreed_TOU.pk
        )

        content = response.render().content.decode("utf-8")
        self.assertNotIn("By unchecking this box and clicking “Update", content)

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
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        cls.bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        cls.proxy_partner_1 = PartnerFactory(authorization_method=Partner.PROXY)

        cls.user_coordinator = UserFactory(username="Jon Snow")
        cls.editor = EditorFactory()
        cls.editor.wp_bundle_eligible = True
        cls.editor.save()
        get_coordinators().user_set.add(cls.user_coordinator)

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

    def test_add_favorite_collection_valid(self):
        """
        Tests that a valid collection (one a user has access to) is successfully
        added to the favorites
        """
        profile = UserProfile.objects.get(user=self.editor.user)

        # Create an authorization object so that the partner can be added to a
        # user's favorites collection

        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        profile.favorites.add(self.bundle_partner_1)
        profile.favorites.add(self.bundle_partner_2)
        profile.favorites.add(self.proxy_partner_1)

        self.assertIn(self.proxy_partner_1, profile.favorites.all())
        self.assertIn(self.bundle_partner_1, profile.favorites.all())
        self.assertIn(self.bundle_partner_2, profile.favorites.all())

    def test_add_favorite_expired_collection_valid(self):
        """
        Tests that a valid collection (one a user has access to, even if it has
        expired) is successfully added to the favorites
        """
        profile = UserProfile.objects.get(user=self.editor.user)

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        someday = date.today() - timedelta(days=60)
        authorization = Authorization.objects.get(
            user=self.editor.user, partners=self.proxy_partner_1
        )
        authorization.date_expires = someday
        authorization.save()

        profile.favorites.add(self.proxy_partner_1)

        self.assertIn(self.proxy_partner_1, profile.favorites.all())

    def test_add_favorite_collection_invalid(self):
        """
        Tests that an invalid collection (one a user does not has access to) is not
        added to the favorites and that a ValidationError is raised
        """
        profile = UserProfile.objects.get(user=self.editor.user)

        with self.assertRaises(ValidationError):
            profile.favorites.add(self.proxy_partner_1)


class EditorModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
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
        cls.editor = EditorFactory(
            wp_username="editor_model_test",
            wp_rights=json.dumps(["cat floofing", "the big red button"]),
            wp_groups=json.dumps(["sysops", "bureaucrats"]),
            wp_registered=None,
        )
        cls.editor.user.userprofile.terms_of_use = True
        cls.editor.user.userprofile.save()
        cls.editor.user.save()
        cls.editor.save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.editor.delete()

    def test_encoder_works_with_special_character_username(self):
        test = Editor().encode_wp_username("editor model&test")
        self.assertEqual(test, "editor%20model%26test")

    def test_wp_user_page_url(self):
        expected_url = settings.TWLIGHT_OAUTH_PROVIDER_URL + "/User:editor_model_test"
        self.assertEqual(expected_url, self.editor.wp_user_page_url)

    def test_wp_link_central_auth(self):
        expected_url = "https://meta.wikimedia.org/w/index.php?title=Special%3ACentralAuth&target=editor_model_test"
        self.assertEqual(expected_url, self.editor.wp_link_central_auth)

    def test_get_wp_rights_display(self):
        expected_text = ["cat floofing", "the big red button"]
        self.assertEqual(expected_text, self.editor.get_wp_rights_display)

    def test_get_wp_groups_display(self):
        expected_text = ["sysops", "bureaucrats"]
        self.assertEqual(expected_text, self.editor.get_wp_groups_display)

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
        self.editor.update_editcount(global_userinfo["editcount"])
        enough_edits = editor_enough_edits(self.editor.wp_editcount)
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        not_blocked = editor_not_blocked(global_userinfo["merged"])
        ignore_wp_blocks = False
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertTrue(valid)

        # Too few edits
        global_userinfo["editcount"] = 499
        self.editor.update_editcount(global_userinfo["editcount"])
        enough_edits = editor_enough_edits(self.editor.wp_editcount)
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertFalse(valid)

        # Oauth says the account is too new, but global_userinfo says it's fine
        global_userinfo["editcount"] = 500
        self.editor.update_editcount(global_userinfo["editcount"])
        enough_edits = editor_enough_edits(self.editor.wp_editcount)
        identity["registered"] = datetime.today().strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertTrue(valid)

        # Oauth says the account is fine, but global_userinfo says it's too new
        global_userinfo["editcount"] = 500
        global_userinfo["registration"] = datetime.today()
        self.editor.update_editcount(global_userinfo["editcount"])
        enough_edits = editor_enough_edits(self.editor.wp_editcount)
        identity["registered"] = (datetime.today() - timedelta(days=365)).strftime(
            "%Y%m%d%H%M%S"
        )
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertTrue(valid)

        # Account created too recently
        global_userinfo["editcount"] = 500
        global_userinfo["registration"] = datetime.today()
        self.editor.update_editcount(global_userinfo["editcount"])
        enough_edits = editor_enough_edits(self.editor.wp_editcount)
        identity["registered"] = datetime.today().strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertFalse(valid)

        # Edge case: this shouldn't work.
        almost_6_months_ago = datetime.today() - timedelta(days=181)
        global_userinfo["registration"] = almost_6_months_ago
        identity["registered"] = almost_6_months_ago.strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertFalse(valid)

        # Edge case: this should work.
        almost_6_months_ago = datetime.today() - timedelta(days=182)
        global_userinfo["registration"] = almost_6_months_ago
        identity["registered"] = almost_6_months_ago.strftime("%Y%m%d%H%M%S")
        registered = editor_reg_date(identity, global_userinfo)
        account_old_enough = editor_account_old_enough(registered)
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertTrue(valid)

        # Bad editor! No biscuit.
        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)
        not_blocked = editor_not_blocked(global_userinfo["merged"])
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertFalse(valid)

        # Aw, you're not that bad. Have a cookie.
        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)
        not_blocked = editor_not_blocked(global_userinfo["merged"])
        ignore_wp_blocks = True
        valid = editor_valid(
            enough_edits, account_old_enough, not_blocked, ignore_wp_blocks
        )
        self.assertTrue(valid)

    def test_is_user_bundle_eligible(self):
        """
        Users must:
        * Be valid
        * Have made 10 edits in the last 30 days (with some wiggle room, as you will see)
        """
        # Valid data
        lang = get_language()
        identity = copy.copy(FAKE_IDENTITY)
        identity["sub"] = self.editor.wp_sub
        identity["editcount"] = 500
        global_userinfo = copy.copy(FAKE_GLOBAL_USERINFO)
        global_userinfo["id"] = self.editor.wp_sub
        global_userinfo["editcount"] = 500

        # 1st time bundle check should always pass for a valid user.
        self.editor.update_from_wikipedia(
            identity, lang, global_userinfo=global_userinfo
        )
        self.editor.refresh_from_db()
        self.assertTrue(self.editor.wp_bundle_eligible)

        # A valid user should pass up to 30 days after their first login, even if they haven't made anymore edits.
        for day in range(29):
            self.editor.update_from_wikipedia(
                identity,
                lang,
                global_userinfo,
                self.editor.wp_editcount_updated + timedelta(days=1),
            )
        self.editor.update_editcount(
            global_userinfo["editcount"],
            self.editor.wp_editcount_updated + timedelta(hours=23, minutes=59),
        )
        self.editor.refresh_from_db()
        self.assertTrue(self.editor.wp_bundle_eligible)

        # A valid user should fail 30 days after their last edit.
        self.editor.update_from_wikipedia(
            identity,
            lang,
            global_userinfo,
            self.editor.wp_editcount_updated + timedelta(minutes=1),
        )
        self.editor.refresh_from_db()
        self.assertFalse(self.editor.wp_bundle_eligible)

        # A valid user should pass if they have made enough recent edits.
        global_userinfo["editcount"] = 510
        self.editor.update_from_wikipedia(
            identity,
            lang,
            global_userinfo,
            self.editor.wp_editcount_updated + timedelta(minutes=1),
        )
        self.editor.refresh_from_db()
        self.assertTrue(self.editor.wp_bundle_eligible)

        # Bad editor! No biscuit, even if you have enough edits.
        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)
        self.editor.update_from_wikipedia(
            identity,
            lang,
            global_userinfo,
            self.editor.wp_editcount_updated + timedelta(minutes=1),
        )

        self.editor.refresh_from_db()
        self.assertEqual(self.editor.wp_editcount, 510)
        self.assertEqual(
            self.editor.wp_editcount_prev(
                current_datetime=self.editor.wp_editcount_updated
            ),
            500,
        )
        self.assertFalse(self.editor.wp_bundle_eligible)

    def test_update_bundle_authorization_creation(self):
        """
        update_bundle_authorization() should create a new bundle
        authorization if one didn't exist when the user is
        bundle eligible.
        """
        editor = EditorFactory()
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        # Check we don't already have a Bundle authorization
        with self.assertRaises(Authorization.DoesNotExist):
            bundle_authorization = Authorization.objects.get(
                user=editor.user, partners__authorization_method=Partner.BUNDLE
            )

        editor.wp_bundle_eligible = True
        editor.save()

        editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()
        # We should now have created a single authorization to
        # Bundle partners.
        self.assertEqual(bundle_authorization.count(), 1)

    def test_update_bundle_authorization_expiry(self):
        """
        update_bundle_authorization() should expire existing bundle
        authorizations if the user is no longer eligible
        """
        editor = EditorFactory()
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        editor.wp_bundle_eligible = True
        editor.save()

        editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        editor.wp_bundle_eligible = False
        editor.save()

        editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        # Authorization should still exist
        self.assertEqual(bundle_authorization.count(), 1)

        # But it should have now expired
        self.assertEqual(
            bundle_authorization.first().date_expires, date.today() - timedelta(days=1)
        )

    def test_update_bundle_authorization_user_eligible_again(self):
        """
        update_bundle_authorization() should undo expiry of existing
        bundle authorizations if the user is now eligible again
        """
        editor = EditorFactory()
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        editor.wp_bundle_eligible = True
        editor.save()

        editor.update_bundle_authorization()

        editor.wp_bundle_eligible = False
        editor.save()

        editor.update_bundle_authorization()

        # Marking them as eligible a 2nd time should update their
        # expired authorization to remove the expiry date.
        editor.wp_bundle_eligible = True
        editor.save()

        editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        # Authorization should still exist
        self.assertEqual(bundle_authorization.count(), 1)

        # It should have no expiry date, i.e. it's now active again.
        self.assertEqual(bundle_authorization.get().date_expires, None)

    def test_wp_bundle_authorized_no_bundle_auth(self):
        """
        If a user has no authorization to Bundle
        resources, wp_bundle_authorized should return False
        """
        editor = EditorFactory()

        self.assertFalse(editor.wp_bundle_authorized)

    def test_wp_bundle_authorized_true(self):
        """
        If a user has an active authorization to Bundle
        resources, wp_bundle_authorized should return True
        """
        editor = EditorFactory()
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        editor.wp_bundle_eligible = True
        editor.save()

        # Create Bundle auth for this user
        editor.update_bundle_authorization()

        self.assertTrue(editor.wp_bundle_authorized)

    def test_wp_bundle_authorized_false(self):
        """
        If a user has an expired authorization to Bundle
        resources, wp_bundle_authorized should return False
        """
        editor = EditorFactory()
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        editor.wp_bundle_eligible = True
        editor.save()

        # Create Bundle auth for this user
        editor.update_bundle_authorization()

        editor.wp_bundle_eligible = False
        editor.save()

        # Expire the user's auth
        editor.update_bundle_authorization()

        self.assertFalse(editor.wp_bundle_authorized)

    def test_update_from_wikipedia(self):
        identity = {}
        identity["username"] = "evil_dr_porkchop"
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity["sub"] = self.editor.wp_sub
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

        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)

        # Don't change self.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory(wp_registered=None)
        new_identity = dict(identity)
        new_global_userinfo = dict(global_userinfo)
        new_identity["sub"] = new_editor.wp_sub
        new_global_userinfo["id"] = new_identity["sub"]

        lang = get_language()
        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
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
        with self.assertRaises(SuspiciousOperation):
            new_identity["sub"] = new_editor.wp_sub + 1
            new_global_userinfo["id"] = new_identity["sub"]
            new_editor.update_from_wikipedia(
                new_identity, lang, new_global_userinfo
            )  # This call also saves the editor

    def test_block_hash_changed_block_override(self):
        """
        Tests that an email is sent when an editor's block status changes and
        the block override is on
        """
        identity = {}
        identity["username"] = "evil_dr_porkchop"
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity["sub"] = self.editor.wp_sub
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

        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS)

        # Don't change self.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory(
            wp_registered=None, wp_block_hash="", ignore_wp_blocks=True
        )
        new_identity = dict(identity)
        new_global_userinfo = dict(global_userinfo)
        new_identity["sub"] = new_editor.wp_sub
        new_global_userinfo["id"] = new_identity["sub"]

        lang = get_language()
        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
        )  # This call also saves the editor

        blocked_dict = editor_make_block_dict(new_global_userinfo["merged"])

        self.assertTrue(check_password(blocked_dict, new_editor.wp_block_hash))
        # No emails should be sent since the wp_block_hash was blank
        self.assertEqual(len(mail.outbox), 0)

        # Add a new block from the user
        copied_merged_blocked_array = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)
        new_global_userinfo["merged"] = copied_merged_blocked_array

        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
        )  # This call also saves the editor

        new_blocked_dict = editor_make_block_dict(new_global_userinfo["merged"])

        self.assertTrue(check_password(new_blocked_dict, new_editor.wp_block_hash))
        self.assertFalse(check_password(blocked_dict, new_editor.wp_block_hash))
        self.assertEqual(len(mail.outbox), 1)

    def test_block_hash_changed_no_block_override(self):
        """
        Tests that an email is not sent when an editor's block status changes and
        the block override is off
        """
        identity = {}
        identity["username"] = "evil_dr_porkchop"
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity["sub"] = self.editor.wp_sub
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

        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS)

        # Don't change self.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory(wp_registered=None, wp_block_hash="")
        new_identity = dict(identity)
        new_global_userinfo = dict(global_userinfo)
        new_identity["sub"] = new_editor.wp_sub
        new_global_userinfo["id"] = new_identity["sub"]

        lang = get_language()
        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
        )  # This call also saves the editor

        blocked_dict = editor_make_block_dict(new_global_userinfo["merged"])

        self.assertTrue(check_password(blocked_dict, new_editor.wp_block_hash))
        # No emails should be sent since the wp_block_hash was blank
        self.assertEqual(len(mail.outbox), 0)

        # Add a new block from the user
        copied_merged_blocked_array = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)
        new_global_userinfo["merged"] = copied_merged_blocked_array

        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
        )  # This call also saves the editor

        new_blocked_dict = editor_make_block_dict(new_global_userinfo["merged"])

        self.assertTrue(check_password(new_blocked_dict, new_editor.wp_block_hash))
        self.assertFalse(check_password(blocked_dict, new_editor.wp_block_hash))
        self.assertEqual(len(mail.outbox), 0)

    def test_block_hash_email_not_sent_on_first_login(self):
        """
        Tests that an email is not sent when an editor's block override
        is turned on and they subsequently login.
        """
        identity = {}
        identity["username"] = "evil_dr_porkchop"
        # Users' unique WP IDs should not change across API calls, but are
        # needed by update_from_wikipedia.
        identity["sub"] = self.editor.wp_sub
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

        global_userinfo["merged"] = copy.copy(FAKE_MERGED_ACCOUNTS)

        # Don't change self.editor, or other tests will fail! Make a new one
        # to test instead.
        new_editor = EditorFactory(wp_registered=None)
        new_identity = dict(identity)
        new_global_userinfo = dict(global_userinfo)
        new_identity["sub"] = new_editor.wp_sub
        new_global_userinfo["id"] = new_identity["sub"]

        # User starts blocked
        copied_merged_blocked_array = copy.copy(FAKE_MERGED_ACCOUNTS_BLOCKED)
        new_global_userinfo["merged"] = copied_merged_blocked_array

        lang = get_language()
        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
        )  # This call also saves the editor

        blocked_dict = editor_make_block_dict(new_global_userinfo["merged"])

        self.assertTrue(check_password(blocked_dict, new_editor.wp_block_hash))
        # No emails should be sent since the wp_block_hash was blank
        self.assertEqual(len(mail.outbox), 0)

        new_editor.ignore_wp_blocks = True
        new_editor.save()

        new_editor.update_from_wikipedia(
            new_identity, lang, new_global_userinfo
        )  # This call also saves the editor

        # The user's block status never changed, so we shouldn't send any
        # emails
        self.assertEqual(len(mail.outbox), 0)


class OAuthTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
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


class AuthorizationsHelpersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        cls.bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)
        cls.bundle_partner_3 = PartnerFactory(authorization_method=Partner.BUNDLE)
        cls.proxy_partner_1 = PartnerFactory(authorization_method=Partner.PROXY)
        cls.proxy_partner_2 = PartnerFactory(authorization_method=Partner.PROXY)

    def test_validate_partners_for_bundle_auth(self):
        """
        Passing a queryset of partners which are all set to
        the BUNDLE authorization method should raise no
        errors
        """
        partner_queryset = Partner.objects.filter(authorization_method=Partner.BUNDLE)
        try:
            validation = validate_partners(partner_queryset)
        except ValidationError:
            self.fail("validate_partners() raised ValidationError unexpectedly.")

    def test_validate_partners_for_mixed_auth_types(self):
        """
        Passing a queryset with both BUNDLE and PROXY authorization
        types to validate_partners() should raise a ValidationError
        """
        partner_queryset = Partner.objects.filter(
            authorization_method__in=[Partner.BUNDLE, Partner.PROXY]
        )
        with self.assertRaises(ValidationError):
            validate_partners(partner_queryset)

    def test_validate_partners_for_wrong_auth_type(self):
        """
        Passing a queryset with multiple PROXY partners
        to validate_partners() should raise a ValidationError
        """
        partner_queryset = Partner.objects.filter(authorization_method=Partner.PROXY)
        with self.assertRaises(ValidationError):
            validate_partners(partner_queryset)

    def test_get_all_bundle_authorizations(self):
        """
        The get_all_bundle_authorizations() helper function
        should return a Queryset of all authorizations
        for the Library Bundle, both active and not.
        """
        editor = EditorFactory()
        editor.wp_bundle_eligible = True
        editor.save()
        # This should create an authorization linked to
        # bundle partners.
        editor.update_bundle_authorization()

        all_auths = get_all_bundle_authorizations()

        # One editor has Bundle auths, so this should be a
        # Queryset with 1 entry.
        self.assertEqual(all_auths.count(), 1)


class ManagementCommandsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        """
        Creates a bundle-eligible editor.
        Returns
        -------
        None
        """
        cls.editor = EditorFactory()
        cls.editor.wp_bundle_eligible = True
        cls.editor.update_editcount(42, now() - timedelta(days=30))
        cls.editor.wp_account_old_enough = True
        cls.editor.user.userprofile.terms_of_use = True
        cls.editor.user.userprofile.save()
        cls.editor.user.save()
        cls.editor.save()

        cls.global_userinfo_editor = {
            "home": "enwiki",
            "id": cls.editor.wp_sub,
            "registration": "2015-11-06T15:46:29Z",  # Well before first commit.
            "name": "user328",
            "editcount": 5000,
            "merged": copy.copy(FAKE_MERGED_ACCOUNTS),
        }

    def test_user_update_eligibility_command_valid(self):
        """
        user_update_eligibility command should check and update Bundle eligible editors correctly.
        Returns
        -------
        None
        """

        # 1st time bundle check should always pass for a valid editor.
        self.assertTrue(self.editor.wp_bundle_eligible)

        # A valid editor should pass editcount checks for 30 days after their first login, even if they haven't made any more edits.
        for day in range(30):
            call_command(
                "user_update_eligibility",
                datetime=datetime.isoformat(
                    self.editor.wp_editcount_updated + timedelta(days=1)
                ),
                wp_username=self.editor.wp_username,
                global_userinfo=self.global_userinfo_editor,
            )
        self.editor.refresh_from_db()
        self.assertEqual(self.editor.wp_editcount, 5000)
        self.assertEqual(
            self.editor.wp_editcount_prev(
                current_datetime=self.editor.wp_editcount_updated
            ),
            42,
        )
        self.assertEqual(
            self.editor.wp_editcount_recent(
                current_datetime=self.editor.wp_editcount_updated
            ),
            4958,
        )
        self.assertTrue(self.editor.wp_bundle_eligible)

        # A valid Editor should fail 31 days after their last edit.
        call_command(
            "user_update_eligibility",
            datetime=datetime.isoformat(
                self.editor.wp_editcount_updated + timedelta(days=1)
            ),
            global_userinfo=self.global_userinfo_editor,
        )
        self.editor.refresh_from_db()
        self.assertFalse(self.editor.wp_bundle_eligible)

        # A valid Editor should then pass if they make at least 10 edits.
        self.global_userinfo_editor["editcount"] = 5010
        call_command(
            "user_update_eligibility",
            datetime=datetime.isoformat(
                self.editor.wp_editcount_updated + timedelta(minutes=1)
            ),
            global_userinfo=self.global_userinfo_editor,
        )
        self.editor.refresh_from_db()
        self.assertEqual(self.editor.wp_editcount, 5010)
        self.assertEqual(
            self.editor.wp_editcount_prev(
                current_datetime=self.editor.wp_editcount_updated
            ),
            5000,
        )
        self.assertEqual(
            self.editor.wp_editcount_recent(self.editor.wp_editcount_updated), 10
        )
        self.assertTrue(self.editor.wp_bundle_eligible)

        # Editors whose editcount has been updated within the last 30 days should be left alone.
        call_command(
            "user_update_eligibility",
            datetime=datetime.isoformat(
                self.editor.wp_editcount_updated
                + timedelta(days=29, hours=23, minutes=59, seconds=59)
            ),
            global_userinfo=self.global_userinfo_editor,
        )

        self.editor.refresh_from_db()
        self.assertEqual(self.editor.wp_editcount, 5010)
        self.assertEqual(
            self.editor.wp_editcount_prev(
                current_datetime=self.editor.wp_editcount_updated
            ),
            5000,
        )
        self.assertEqual(
            self.editor.wp_editcount_recent(
                current_datetime=self.editor.wp_editcount_updated
            ),
            10,
        )
        self.assertTrue(self.editor.wp_bundle_eligible)

    def test_user_update_eligibility_command_terms_not_accepted(self):
        """
        Editors who don't agree to terms are not bundle eligible.
        Returns
        -------
        None
        """
        # The editor hasn't accepted the terms of use
        self.editor.user.userprofile.terms_of_use = False
        self.editor.user.userprofile.save()
        self.editor.user.save()
        self.editor.save()

        self.assertTrue(self.editor.wp_bundle_eligible)

        call_command(
            "user_update_eligibility",
            datetime=datetime.isoformat(
                self.editor.wp_editcount_updated + timedelta(days=1)
            ),
            wp_username=self.editor.wp_username,
            global_userinfo=self.global_userinfo_editor,
        )

        self.editor.refresh_from_db()

        self.assertFalse(self.editor.wp_bundle_eligible)


class MyLibraryViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.bundle_partner_1 = PartnerFactory(
            authorization_method=Partner.BUNDLE,
            new_tags={"tags": ["earth-sciences_tag"]},
            searchable=Partner.SEARCHABLE,
        )
        cls.bundle_partner_2 = PartnerFactory(
            authorization_method=Partner.BUNDLE,
            new_tags={"tags": ["art_tag"]},
            searchable=Partner.PARTIALLY_SEARCHABLE,
        )

        cls.bundle_partner_3 = PartnerFactory(
            authorization_method=Partner.BUNDLE,
            searchable=Partner.PARTIALLY_SEARCHABLE,
        )
        cls.bundle_partner_3.new_tags = {"tags": ["art_tag"]}
        cls.bundle_partner_3.save()

        cls.bundle_partner_4 = PartnerFactory(
            authorization_method=Partner.BUNDLE,
            searchable=Partner.SEARCHABLE,
        )
        cls.bundle_partner_4.new_tags = {"tags": ["multidisciplinary_tag"]}
        cls.bundle_partner_4.save()

        cls.proxy_partner_1 = PartnerFactory(
            authorization_method=Partner.PROXY,
            searchable=Partner.SEARCHABLE,
        )
        cls.proxy_partner_1.new_tags = {"tags": ["earth-sciences_tag"]}
        cls.proxy_partner_1.save()

        cls.proxy_partner_2 = PartnerFactory(
            authorization_method=Partner.PROXY,
            searchable=Partner.SEARCHABLE,
        )
        cls.proxy_partner_2.new_tags = {"tags": ["earth-sciences_tag"]}
        cls.proxy_partner_2.save()

        cls.proxy_partner_3 = PartnerFactory(authorization_method=Partner.PROXY)
        cls.proxy_partner_3.new_tags = {"tags": ["multidisciplinary_tag"]}
        cls.proxy_partner_3.save()

        cls.email_partner_1 = PartnerFactory(authorization_method=Partner.EMAIL)
        cls.email_partner_2 = PartnerFactory(authorization_method=Partner.EMAIL)

        cls.user_coordinator = UserFactory(username="Jon Snow")
        cls.editor = EditorFactory()
        cls.editor.wp_bundle_eligible = True
        cls.editor.save()
        get_coordinators().user_set.add(cls.user_coordinator)

    def test_user_collections(self):
        """
        Tests that only user collections are shown
        """
        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_3 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_3,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_4 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_4,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.bundle_partner_1.company_name), content)
        self.assertIn(escape(self.bundle_partner_2.company_name), content)
        self.assertIn(escape(self.bundle_partner_3.company_name), content)
        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn(escape(self.bundle_partner_4.company_name), content)
        # Even though this partner is not visible, it still appears in the HTML
        # render
        self.assertIn(escape(self.proxy_partner_2.company_name), content)
        self.assertIn(escape(self.proxy_partner_3.company_name), content)

    def test_user_collections_show_expiry_date_extend(self):
        """
        Tests that the expiry date and the Extend button are shown
        """
        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        someday = date.today() + timedelta(days=60)
        authorization = Authorization.objects.get(
            user=self.editor.user, partners=self.proxy_partner_1
        )
        authorization.date_expires = someday
        authorization.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        someday_fmt = datetime.strftime(someday, "%b %d, %Y")
        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn(someday_fmt, content)
        self.assertIn("Extend", content)

    def test_user_collections_show_expiry_date_renew(self):
        """
        Tests that the expiry date and the Renew button are shown
        """
        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        someday = date.today() - timedelta(days=60)
        authorization = Authorization.objects.get(
            user=self.editor.user, partners=self.proxy_partner_1
        )
        authorization.date_expires = someday
        authorization.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        someday_fmt = datetime.strftime(someday, "%b %d, %Y")
        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn(someday_fmt, content)
        self.assertIn("Renew", content)

    def test_user_collections_show_expiry_date_not_shown(self):
        """
        Tests that the expiry date is not shown
        """
        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        authorization = Authorization.objects.get(
            user=self.editor.user, partners=self.proxy_partner_1
        )
        authorization.date_expires = None
        authorization.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertNotIn("Expiry date: ", content)

    def test_user_collections_has_open_application(self):
        """
        Tests that the Go to application button is shown when an application is open
        """

        old_app = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.PENDING,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        authorization = Authorization.objects.get(
            user=self.editor.user, partners=self.proxy_partner_1
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn("Go to application", content)

    def test_collection_filters_art_tag(self):
        """
        Tests that only user collections that match the filter are shown
        """
        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_3 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_3,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_4 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_4,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_art_tag_param = "{url}?tags=art_tag".format(url=url)
        request = factory.get(url_with_art_tag_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.bundle_partner_2.company_name), content)
        self.assertIn(escape(self.bundle_partner_3.company_name), content)
        # Multidisciplinary partners should also appear when filtering
        self.assertIn(escape(self.bundle_partner_4.company_name), content)
        self.assertIn(escape(self.proxy_partner_3.company_name), content)

        self.assertNotIn(escape(self.bundle_partner_1.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_1.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_2.company_name), content)

    def test_collection_filters_earth_sciences_tag(self):
        """
        Tests that only user collections that match the filter are shown
        """
        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_3 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_3,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_4 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_4,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_earth_sciences_tag_param = "{url}?tags=earth-sciences_tag".format(
            url=url
        )
        request = factory.get(url_with_earth_sciences_tag_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertNotIn(escape(self.bundle_partner_2.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_3.company_name), content)
        # Multidisciplinary partners should also appear when filtering
        self.assertIn(escape(self.bundle_partner_4.company_name), content)
        self.assertIn(escape(self.proxy_partner_3.company_name), content)

        self.assertIn(escape(self.bundle_partner_1.company_name), content)
        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn(escape(self.proxy_partner_2.company_name), content)

    def test_collection_show_waitlisted_badge(self):
        """
        Tests that the Waitlisted badge is shown because the authorization has expired
        """
        waitlisted_partner = PartnerFactory(
            authorization_method=Partner.PROXY, status=Partner.WAITLIST
        )
        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=waitlisted_partner,
            sent_by=self.user_coordinator,
        )

        someday = date.today() - timedelta(days=60)
        authorization = Authorization.objects.get(
            user=self.editor.user, partners=waitlisted_partner
        )
        authorization.date_expires = someday
        authorization.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(waitlisted_partner.company_name), content)
        self.assertIn("Waitlisted", content)

    def test_collection_dont_show_waitlisted_badge(self):
        """
        Tests that the Waitlisted badge is not shown because the authorization has not expired
        """
        waitlisted_partner = PartnerFactory(
            authorization_method=Partner.PROXY, status=Partner.WAITLIST
        )
        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=waitlisted_partner,
            sent_by=self.user_coordinator,
        )

        someday = date.today() + timedelta(days=60)
        authorization = Authorization.objects.get(
            user=self.editor.user, partners=waitlisted_partner
        )
        authorization.date_expires = someday
        authorization.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(waitlisted_partner.company_name), content)
        self.assertNotIn("Waitlisted", content)

    def test_collection_show_not_available_badge(self):
        """
        Tests that the Not Available badge is shown
        """
        not_available_partner = PartnerFactory(
            authorization_method=Partner.PROXY, status=Partner.NOT_AVAILABLE
        )

        # Make the user staff so they can see unavailable collections
        self.editor.user.is_staff = True
        self.editor.user.save()
        self.editor.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(not_available_partner.company_name), content)
        self.assertIn("Not Available", content)

    def test_user_not_eligible_eligibility_modal_shown(self):
        """
        Tests that, when a user is not eligible to access the library, the eligibility
        modal will be shown
        """
        # Make the user not eligible so they can see the eligibility modal
        self.editor.wp_bundle_eligible = False
        self.editor.save()

        factory = RequestFactory()
        url = reverse("users:my_library")
        request = factory.get(url)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        eligibility_message = "Sorry, your Wikipedia account doesn’t currently qualify to access The Wikipedia Library."

        self.assertIn(eligibility_message, content)

    def test_collection_filters_searchable(self):
        """
        Tests that only user collections that match the filter are shown
        """
        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_3 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_3,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_4 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_4,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_searchable_param = "{url}?searchable={searchable}".format(
            url=url, searchable=Partner.SEARCHABLE
        )
        request = factory.get(url_with_searchable_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.bundle_partner_1.company_name), content)
        self.assertIn(escape(self.bundle_partner_4.company_name), content)
        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn(escape(self.proxy_partner_2.company_name), content)

        self.assertNotIn(escape(self.bundle_partner_2.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_3.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_3.company_name), content)

    def test_collection_filters_partially_searchable(self):
        """
        Tests that only user collections that match the filter are shown
        """
        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_3 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_3,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_4 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_4,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_searchable_param = "{url}?searchable={searchable}".format(
            url=url, searchable=Partner.PARTIALLY_SEARCHABLE
        )
        request = factory.get(url_with_searchable_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.bundle_partner_2.company_name), content)
        self.assertIn(escape(self.bundle_partner_3.company_name), content)

        self.assertNotIn(escape(self.bundle_partner_1.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_4.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_1.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_2.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_3.company_name), content)

    def test_collection_filters_not_searchable(self):
        """
        Tests that only user collections that match the filter are shown
        """
        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_3 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_3,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_4 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_4,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_searchable_param = "{url}?searchable={searchable}".format(
            url=url, searchable=Partner.NOT_SEARCHABLE
        )
        request = factory.get(url_with_searchable_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.proxy_partner_3.company_name), content)

        self.assertNotIn(escape(self.bundle_partner_1.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_2.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_3.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_4.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_1.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_2.company_name), content)

    def test_instant_access_filter(self):
        """
        Tests that only instant access collections are shown
        """

        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_2,
            sent_by=self.user_coordinator,
        )

        app_email_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.email_partner_1,
            sent_by=self.user_coordinator,
        )

        app_email_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )
        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_access_param = "{url}?access={access}".format(url=url, access=INSTANT)
        request = factory.get(url_with_access_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.bundle_partner_1.company_name), content)
        self.assertIn(escape(self.bundle_partner_2.company_name), content)
        self.assertIn(escape(self.proxy_partner_1.company_name), content)
        self.assertIn(escape(self.proxy_partner_2.company_name), content)

        self.assertNotIn(escape(self.email_partner_1.company_name), content)
        self.assertNotIn(escape(self.email_partner_2.company_name), content)

    def test_multi_step_access_filter(self):
        """
        Tests that only instant access collections are shown
        """

        app_bundle_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_1,
            sent_by=self.user_coordinator,
        )

        app_bundle_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_1,
            sent_by=self.user_coordinator,
        )

        app_proxy_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.proxy_partner_2,
            sent_by=self.user_coordinator,
        )

        app_email_partner_1 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.email_partner_1,
            sent_by=self.user_coordinator,
        )

        app_email_partner_2 = ApplicationFactory(
            status=Application.SENT,
            editor=self.editor,
            partner=self.bundle_partner_2,
            sent_by=self.user_coordinator,
        )
        factory = RequestFactory()
        url = reverse("users:my_library")
        url_with_access_param = "{url}?access={access}".format(
            url=url, access=MULTI_STEP
        )
        request = factory.get(url_with_access_param)
        request.user = self.editor.user
        response = MyLibraryView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.render().content.decode("utf-8")

        self.assertNotIn(escape(self.bundle_partner_1.company_name), content)
        self.assertNotIn(escape(self.bundle_partner_2.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_1.company_name), content)
        self.assertNotIn(escape(self.proxy_partner_2.company_name), content)

        self.assertIn(escape(self.email_partner_1.company_name), content)
        self.assertIn(escape(self.email_partner_2.company_name), content)
