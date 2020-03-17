# -*- coding: utf-8 -*-
import csv
from datetime import date, timedelta
from unittest.mock import patch
import os
import random

from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import Http404
from django.test import Client, TestCase, RequestFactory
from django.utils.html import escape

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.users.factories import EditorFactory, UserProfileFactory, UserFactory
from TWLight.users.groups import get_coordinators, get_restricted
from TWLight.users.models import Authorization

from .factories import PartnerFactory, StreamFactory
from .models import Language, RESOURCE_LANGUAGES, Partner, AccessCode
from .views import PartnersDetailView, PartnersFilterView, PartnersToggleWaitlistView
from .filters import PartnerFilter

from . import views


def EditorCraftRoom(
    self, Terms=False, Coordinator=False, Restricted=False, editor=None
):
    """
    The use of the @login_required decorator on many views precludes the use of
    factories for many tests. This method creates an Editor logged into a test
    client session.
    """
    terms_url = reverse("terms")

    # Create editor if None was specified.
    if not editor:
        editor = EditorFactory()

    # Set a password
    editor.user.set_password("editor")
    editor.user.save()

    # Log user in
    self.client = Client()
    session = self.client.session
    self.client.login(username=editor.user.username, password="editor")

    # Agree to terms of use in Client (or not).
    if Terms:
        terms = self.client.get(terms_url, follow=True)
        terms_form = terms.context["form"]
        data = terms_form.initial
        data["terms_of_use"] = True
        data["submit"] = True
        agree = self.client.post(terms_url, data)

    # Add or remove editor from Coordinators as required
    coordinators = get_coordinators()

    # Add or remove editor from Restricted as required
    restricted = get_restricted()

    if Coordinator:
        coordinators.user_set.add(editor.user)
    else:
        coordinators.user_set.remove(editor.user)
    if Restricted:
        restricted.user_set.add(editor.user)
    else:
        restricted.user_set.remove(editor.user)

    return editor


class LanguageModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        The uniqueness constraint on Language.language can cause tests to fail
        due to IntegrityErrors as we try to create new languages unless we are
        careful, so let's use get_or_create, not create. (The Django database
        truncation that runs between tests isn't sufficient, since it drops the
        primary key but doesn't delete the fields.)
        """
        super(LanguageModelTests, cls).setUpClass()
        cls.lang_en, _ = Language.objects.get_or_create(language="en")
        cls.lang_fr, _ = Language.objects.get_or_create(language="fr")

    def test_validation(self):
        # Note that RESOURCE_LANGUAGES is a list of tuples, such as
        # `('en', 'English')`, but we only care about the first element of each
        # tuple, as it is the one stored in the database.
        language_codes = [lang[0] for lang in RESOURCE_LANGUAGES]

        not_a_language = "fksdja"
        assert not_a_language not in language_codes
        bad_lang = Language(language=not_a_language)
        with self.assertRaises(ValidationError):
            bad_lang.save()

    def test_language_display(self):
        self.assertEqual(self.lang_en.__str__(), "English")

    def test_language_uniqueness(self):
        with self.assertRaises(IntegrityError):
            lang = Language(language="en")
            lang.save()


class PartnerModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PartnerModelTests, cls).setUpClass()
        cls.lang_en, _ = Language.objects.get_or_create(language="en")
        cls.lang_fr, _ = Language.objects.get_or_create(language="fr")

        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)
        UserProfileFactory(user=editor.user, terms_of_use=True)

        cls.coordinator = editor.user

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super(PartnerModelTests, cls).tearDownClass()
        cls.message_patcher.stop()

    def test_get_languages(self):
        partner = PartnerFactory()

        # At first, the list of languages should be empty.
        self.assertFalse(partner.languages.all())

        partner.languages.add(self.lang_en)
        self.assertEqual(
            list(partner.get_languages), [Language.objects.get(language="en")]
        )

        partner.languages.add(self.lang_fr)
        self.assertIn(Language.objects.get(language="fr"), list(partner.get_languages))

    def test_visibility_of_not_available_1(self):
        """Regular users shouldn't see NOT_AVAILABLE partner pages."""
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        detail_url = partner.get_absolute_url()

        editor = EditorFactory()

        request = RequestFactory().get(detail_url)
        request.user = editor.user
        with self.assertRaises(Http404):
            # We must explicitly pass kwargs to the view even though they are
            # implied by the URL.
            _ = PartnersDetailView.as_view()(request, pk=partner.pk)

    def test_visibility_of_not_available_2(self):
        """
        Regular users shouldn't be able to see NOT_AVAILABLE partners in the
        listview.
        """
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        filter_url = reverse("partners:filter")

        editor = EditorFactory()

        request = RequestFactory().get(filter_url)
        request.user = editor.user
        response = PartnersFilterView.as_view(filterset_class=PartnerFilter)(request)

        self.assertNotContains(response, partner.get_absolute_url())

    def test_visibility_of_not_available_3(self):
        """
        Staff users *should* see NOT_AVAILABLE partner pages.
        We won't test to see if they include the message, because RequestFactory
        doesn't include message middleware, but we can't use the Django test
        client to log in users without passwords (which is our normal user).
        """
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        detail_url = partner.get_absolute_url()

        editor = EditorFactory()
        editor.user.is_staff = True
        editor.user.save()

        request = RequestFactory().get(detail_url)
        request.user = editor.user

        # This should not raise Http404.
        response = PartnersDetailView.as_view()(request, pk=partner.pk)
        self.assertEqual(response.status_code, 200)

    def test_visibility_of_not_available_4(self):
        """
        Staff users *should* see NOT_AVAILABLE partner pages in the list view.
        """
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        filter_url = reverse("partners:filter")

        editor = EditorFactory()
        editor.user.is_staff = True
        editor.user.save()

        request = RequestFactory().get(filter_url)
        request.user = editor.user
        response = PartnersFilterView.as_view(filterset_class=PartnerFilter)(request)

        self.assertContains(response, partner.get_absolute_url())

    def test_visibility_of_not_available_5(self):
        """
        Coordinators *should* see NOT_AVAILABLE partner pages.
        We won't test to see if they include the message, because RequestFactory
        doesn't include message middleware, but we can't use the Django test
        client to log in users without passwords (which is our normal user).
        """
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        detail_url = partner.get_absolute_url()

        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)

        partner.coordinator = editor.user
        partner.save()

        request = RequestFactory().get(detail_url)
        request.user = editor.user

        # This should not raise Http404.
        response = PartnersDetailView.as_view()(request, pk=partner.pk)
        self.assertEqual(response.status_code, 200)

    def test_review_app_page_excludes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.PENDING)

        url = reverse("applications:list")

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Test response.
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, escape(partner.company_name))

    def test_renew_app_page_excludes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)

        tomorrow = date.today() + timedelta(days=1)
        _ = ApplicationFactory(partner=partner, status=Application.SENT)
        url = reverse("applications:list_renewal")

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Test response.
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, escape(partner.company_name))

    def test_sent_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.SENT)
        url = reverse("applications:list_sent")

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # reponse for view when user isn't the designated coordinator
        denyResponse = self.client.get(url, follow=True)

        # Designate the coordinator
        partner.coordinator = editor.user
        partner.save()

        # response for view when user is the designated coordinator
        allowResponse = self.client.get(url, follow=True)

        # Applications should not be visible to just any coordinator
        self.assertNotContains(denyResponse, escape(partner.company_name))

        # Applications should be visible to the designated coordinator
        self.assertContains(allowResponse, escape(partner.company_name))

    def test_rejected_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.NOT_APPROVED)
        url = reverse("applications:list_rejected")

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # reponse for view when user isn't the designated coordinator
        denyResponse = self.client.get(url, follow=True)

        # Designate the coordinator
        partner.coordinator = editor.user
        partner.save()

        # reponse for view when user is the designated coordinator
        allowResponse = self.client.get(url, follow=True)

        # Applications should not be visible to just any coordinator
        self.assertNotContains(denyResponse, escape(partner.company_name))

        # Applications should be visible to the designated coordinator
        self.assertContains(allowResponse, escape(partner.company_name))

    def test_approved_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.APPROVED)
        url = reverse("applications:list_approved")

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # reponse for view when user isn't the designated coordinator
        denyResponse = self.client.get(url, follow=True)

        # Designate the coordinator
        partner.coordinator = editor.user
        partner.save()

        # reponse for view when user is the designated coordinator
        allowResponse = self.client.get(url, follow=True)

        # Applications should not be visible to just any coordinator
        self.assertNotContains(denyResponse, escape(partner.company_name))

        # Applications should be visible to the designated coordinator
        self.assertContains(allowResponse, escape(partner.company_name))

    def test_statuses_exist(self):
        """
        AVAILABLE, NOT_AVAILABLE, WAITLIST should be the status choices.
        """

        assert hasattr(Partner, "AVAILABLE")
        assert hasattr(Partner, "NOT_AVAILABLE")
        assert hasattr(Partner, "WAITLIST")

        assert hasattr(Partner, "STATUS_CHOICES")

        assert len(Partner.STATUS_CHOICES) == 3

        database_statuses = [x[0] for x in Partner.STATUS_CHOICES]

        assert Partner.AVAILABLE in database_statuses
        assert Partner.NOT_AVAILABLE in database_statuses
        assert Partner.WAITLIST in database_statuses

    def test_is_waitlisted(self):
        partner = PartnerFactory(status=Partner.AVAILABLE)
        self.assertFalse(partner.is_waitlisted)
        partner.delete()

        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        self.assertFalse(partner.is_waitlisted)
        partner.delete()

        partner = PartnerFactory(status=Partner.WAITLIST)
        self.assertTrue(partner.is_waitlisted)
        partner.delete()

    def test_default_manager(self):
        """
        The default manager should return AVAILABLE and WAITLIST partners, but
        not NOT_AVAILABLE.
        """
        partner = PartnerFactory(status=Partner.AVAILABLE)
        partner2 = PartnerFactory(status=Partner.NOT_AVAILABLE)
        partner3 = PartnerFactory(status=Partner.WAITLIST)

        all_partners = Partner.objects.all()
        assert partner in all_partners
        assert partner2 not in all_partners
        assert partner3 in all_partners

        # assertQuerysetEqual compares a queryset to a list of representations.
        # Sigh.
        self.assertQuerysetEqual(
            Partner.objects.all(),
            list(
                map(
                    repr,
                    Partner.even_not_available.filter(
                        status__in=[Partner.WAITLIST, Partner.AVAILABLE]
                    ),
                )
            ),
        )


class WaitlistBehaviorTests(TestCase):
    """
    Tests of user-visible behavior with respect to waitlist status. We're
    *not* testing particular HTML messages as those kinds of tests tend to be
    extremely brittle.
    """

    @classmethod
    def setUpClass(cls):
        super(WaitlistBehaviorTests, cls).setUpClass()
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    def test_request_application_view_context_1(self):
        """
        The any_waitlisted context on RequestApplicationView should True if
        there are waitlisted Partners.
        """
        # Set up request.
        req_url = reverse("applications:request")

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        # Ensure there is at least one waitlisted partner.
        partner = PartnerFactory(status=Partner.WAITLIST)

        # Test response.
        response = self.client.get(req_url, follow=True)
        self.assertEqual(response.context["any_waitlisted"], True)

    def test_request_application_view_context_2(self):
        """
        The any_waitlisted context on RequestApplicationView should False if
        there are not waitlisted Partners.
        """
        # Set up request.
        req_url = reverse("applications:request")

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        # Ensure there are no waitlisted partners.
        for partner in Partner.objects.filter(status=Partner.WAITLIST):
            partner.delete()

        # Test response.
        response = self.client.get(req_url, follow=True)
        self.assertEqual(response.context["any_waitlisted"], False)

    def test_toggle_waitlist_1(self):
        """
        Posting to the toggle waitlist view sets an AVAILABLE partner to
        WAITLIST.
        """
        # Create needed objects.
        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)
        UserProfileFactory(user=editor.user, terms_of_use=True)

        partner = PartnerFactory(status=Partner.AVAILABLE)

        # Set up request.
        url = reverse("partners:toggle_waitlist", kwargs={"pk": partner.pk})

        request = RequestFactory().post(url)
        request.user = editor.user

        _ = PartnersToggleWaitlistView.as_view()(request, pk=partner.pk)
        partner.refresh_from_db()
        self.assertEqual(partner.status, Partner.WAITLIST)

    def test_toggle_waitlist_2(self):
        """
        Posting to the toggle waitlist view sets a WAITLIST partner to
        AVAILABLE.
        """
        # Create needed objects.
        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)
        UserProfileFactory(user=editor.user, terms_of_use=True)

        partner = PartnerFactory(status=Partner.WAITLIST)

        # Set up request.
        url = reverse("partners:toggle_waitlist", kwargs={"pk": partner.pk})

        request = RequestFactory().post(url)
        request.user = editor.user

        _ = PartnersToggleWaitlistView.as_view()(request, pk=partner.pk)
        partner.refresh_from_db()
        self.assertEqual(partner.status, Partner.AVAILABLE)

    def test_toggle_waitlist_access(self):
        """
        Only coordinators can post to the toggle waitlist view.
        """
        # Create needed objects.
        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)
        UserProfileFactory(user=editor.user, terms_of_use=True)

        partner = PartnerFactory(status=Partner.AVAILABLE)

        # Set up request.
        url = reverse("partners:toggle_waitlist", kwargs={"pk": partner.pk})

        request = RequestFactory().post(url)
        request.user = editor.user

        # This should work and not throw an error.
        resp = PartnersToggleWaitlistView.as_view()(request, pk=partner.pk)

        coordinators.user_set.remove(editor.user)
        with self.assertRaises(PermissionDenied):
            _ = PartnersToggleWaitlistView.as_view()(request, pk=partner.pk)


class StreamModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(StreamModelTests, cls).setUpClass()
        cls.lang_en, _ = Language.objects.get_or_create(language="en")
        cls.lang_fr, _ = Language.objects.get_or_create(language="fr")

    def test_get_languages(self):
        stream = StreamFactory()

        # At first, the list of languages should be empty.
        self.assertFalse(stream.languages.all())

        stream.languages.add(self.lang_en)
        self.assertEqual(stream.get_languages, "English")

        # Order isn't important.
        stream.languages.add(self.lang_fr)
        self.assertIn(stream.get_languages, ["English, français", "français, English"])


class PartnerViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PartnerViewTests, cls).setUpClass()

        cls.partner = PartnerFactory()
        editor = EditorFactory()
        cls.user = UserFactory(editor=editor)
        cls.coordinator = UserFactory()
        cls.coordinator2 = UserFactory()

        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)
        coordinators.user_set.add(cls.coordinator2)

        cls.application = ApplicationFactory(
            partner=cls.partner, editor=editor, status=Application.SENT
        )

        cls.partner.coordinator = cls.coordinator
        cls.partner.save()

        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    def test_users_view(self):
        users_url = reverse("partners:users", kwargs={"pk": self.partner.pk})

        factory = RequestFactory()
        request = factory.get(users_url)
        request.user = AnonymousUser()

        # Anonymous users can't view the user list
        with self.assertRaises(PermissionDenied):
            _ = views.PartnerUsers.as_view()(request, pk=self.partner.pk)

        request.user = self.user
        # Non-coordinators can't view the user list, even if they have
        # an application for the partner.
        with self.assertRaises(PermissionDenied):
            _ = views.PartnerUsers.as_view()(request, pk=self.partner.pk)

        request.user = self.coordinator2
        # Unassigned coordinators can't view the user list
        with self.assertRaises(PermissionDenied):
            _ = views.PartnerUsers.as_view()(request, pk=self.partner.pk)

        request.user = self.coordinator
        # The assigned coordinator can see the user list!
        response = views.PartnerUsers.as_view()(request, pk=self.partner.pk)
        self.assertEqual(response.status_code, 200)


class CSVUploadTest(TestCase):  # Migrated from staff dashboard test
    @classmethod
    def setUpClass(cls):
        super(CSVUploadTest, cls).setUpClass()

        cls.staff_user = UserFactory(username="staff_user", is_staff=True)
        cls.staff_user.set_password("staff")
        cls.staff_user.save()
        cls.user = UserFactory()

        cls.partner1 = PartnerFactory()
        cls.partner1_pk = cls.partner1.pk
        cls.partner2 = PartnerFactory()
        cls.partner2_pk = cls.partner2.pk
        cls.partner3 = PartnerFactory()
        cls.partner3_pk = cls.partner3.pk

        cls.url = reverse("admin:resources_accesscode_changelist")
        # import url is added inside admin.py so just manually add it here.
        cls.url = cls.url + "import/"

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super(CSVUploadTest, cls).tearDownClass()
        cls.staff_user.delete()
        cls.user.delete()

        # If one of the tests made a csv, delete it.
        if os.path.exists("accesscodes.csv"):
            os.remove("accesscodes.csv")

        cls.message_patcher.stop()

    def test_csv_upload(self):
        """
        A csv file with unique codes for multiple partners should
        upload successfully and create the relevant objects.
        """
        test_file = open("accesscodes.csv", "w", newline="")
        csv_writer = csv.writer(test_file)
        csv_writer.writerow(("ABCD-EFGH-IJKL", str(self.partner1_pk)))
        csv_writer.writerow(("BBCD-EFGH-IJKL", str(self.partner1_pk)))
        csv_writer.writerow(("CBCD-EFGH-IJKL", str(self.partner2_pk)))
        test_file.close()

        client = Client()
        session = client.session
        client.login(username=self.staff_user.username, password="staff")

        with open("accesscodes.csv", "r") as csv_file:
            response = client.post(self.url, {"access_code_csv": csv_file})

        access_codes = AccessCode.objects.all()
        self.assertEqual(access_codes.count(), 3)

    def test_csv_duplicate(self):
        """
        A csv file with non-unique codes for multiple partners should
        only upload the unique ones.
        """
        test_file = open("accesscodes.csv", "w", newline="")
        csv_writer = csv.writer(test_file)
        csv_writer.writerow(("ABCD-EFGH-IJKL", str(self.partner1_pk)))
        csv_writer.writerow(("BBCD-EFGH-IJKL", str(self.partner1_pk)))
        csv_writer.writerow(("ABCD-EFGH-IJKL", str(self.partner1_pk)))
        test_file.close()

        client = Client()
        session = client.session
        client.login(username=self.staff_user.username, password="staff")

        with open("accesscodes.csv", "r") as csv_file:
            response = client.post(self.url, {"access_code_csv": csv_file})

        access_codes = AccessCode.objects.all()
        self.assertEqual(access_codes.count(), 2)

    def test_csv_formatting(self):
        """
        An incorrectly formatted csv shouldn't upload anything.
        """
        test_file = open("accesscodes.csv", "w", newline="")
        csv_writer = csv.writer(test_file)
        csv_writer.writerow(("ABCD-EFGH-IJKL", "EBSCO"))
        csv_writer.writerow(("BBCD-EFGH-IJKL", "JSTOR"))
        csv_writer.writerow(("ABCD-EFGH-IJKL", "BMJ"))
        test_file.close()

        client = Client()
        session = client.session
        client.login(username=self.staff_user.username, password="staff")

        with open("accesscodes.csv", "r") as csv_file:
            response = client.post(self.url, {"access_code_csv": csv_file})

        access_codes = AccessCode.objects.all()
        self.assertEqual(access_codes.count(), 0)


class AutoWaitlistDisableTest(TestCase):
    def setUp(self):
        super(AutoWaitlistDisableTest, self).setUp()
        editor = EditorFactory()
        self.user = editor.user

        self.partner = PartnerFactory(
            status=Partner.WAITLIST,
            authorization_method=Partner.PROXY,
            accounts_available=10,
        )
        self.partner1 = PartnerFactory(
            status=Partner.WAITLIST,
            authorization_method=Partner.PROXY,
            accounts_available=2,
        )

        self.application = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=self.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.application1 = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=self.partner1,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.coordinator = UserFactory(username="coordinator")
        self.coordinator.set_password("coordinator")
        coordinators = get_coordinators()
        coordinators.user_set.add(self.coordinator)
        self.coordinator.userprofile.terms_of_use = True
        self.coordinator.userprofile.save()

        auth1 = Authorization.objects.create(
            user=self.user, authorizer=self.coordinator, date_expires=date.today()
        )
        auth1.partners.add(self.partner)

        auth2 = Authorization.objects.create(
            user=EditorFactory().user,
            authorizer=self.coordinator,
            date_expires=date.today(),
        )
        auth2.partners.add(self.partner)

        auth3 = Authorization.objects.create(
            user=self.user,
            authorizer=self.coordinator,
            date_expires=date.today() + timedelta(days=random.randint(1, 5)),
        )
        auth3.partners.add(self.partner1)

        auth4 = Authorization.objects.create(
            user=EditorFactory().user,
            authorizer=self.coordinator,
            date_expires=date.today() + timedelta(days=random.randint(1, 5)),
        )
        auth4.partners.add(self.partner1)

        self.message_patcher = patch("TWLight.applications.views.messages.add_message")
        self.message_patcher.start()

    def tearDown(self):
        super(AutoWaitlistDisableTest, self).tearDown()
        self.message_patcher.stop()

    def test_auto_disable_waitlist_command(self):
        self.assertEqual(self.partner.status, Partner.WAITLIST)
        self.assertEqual(self.partner1.status, Partner.WAITLIST)

        call_command("proxy_waitlist_disable")

        self.partner.refresh_from_db()
        self.assertEqual(self.partner.status, Partner.AVAILABLE)
        # No change should've been made to the partner with zero accounts available
        self.partner1.refresh_from_db()
        self.assertEqual(self.partner1.status, Partner.WAITLIST)
