# -*- coding: utf-8 -*-
import csv
from datetime import date, timedelta
import json
from jsonschema import validate
import os
import random
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.urls import reverse
from django.db import IntegrityError
from django.http import Http404
from django.test import Client, TestCase, RequestFactory
from django.utils.html import escape

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.users.factories import EditorFactory, UserProfileFactory, UserFactory
from TWLight.users.groups import get_coordinators, get_restricted
from TWLight.users.helpers.authorizations import get_all_bundle_authorizations
from TWLight.users.models import Authorization

from .factories import PartnerFactory, SuggestionFactory
from .helpers import (
    check_for_target_url_duplication_and_generate_error_message,
    get_partner_description_json_schema,
)
from .models import (
    Language,
    RESOURCE_LANGUAGES,
    Partner,
    AccessCode,
    Suggestion,
)
from .views import (
    PartnersDetailView,
    PartnersFilterView,
    PartnersToggleWaitlistView,
    PartnerSuggestionView,
    SuggestionMergeView,
    SuggestionDeleteView,
    SuggestionUpvoteView,
)
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
    def setUpTestData(cls):
        super().setUpTestData()
        """
        The uniqueness constraint on Language.language can cause tests to fail
        due to IntegrityErrors as we try to create new languages unless we are
        careful, so let's use get_or_create, not create. (The Django database
        truncation that runs between tests isn't sufficient, since it drops the
        primary key but doesn't delete the fields.)
        """
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
    def setUpTestData(cls):
        super().setUpTestData()
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
        super().tearDownClass()
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
        # This must raise a PermissionDenied exception
        with self.assertRaises(PermissionDenied):
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
        response = PartnersFilterView.as_view()(request)

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
        response = PartnersFilterView.as_view()(request)

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
        _ = ApplicationFactory(
            partner=partner, status=Application.SENT, sent_by=self.coordinator
        )
        url = reverse("applications:list_renewal")

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Test response.
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, escape(partner.company_name))

    def test_sent_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(
            partner=partner, status=Application.SENT, sent_by=self.coordinator
        )
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

    def test_helper_function_for_target_url_uniqueness(self):
        partner1 = PartnerFactory(authorization_method=Partner.PROXY)
        partner2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        example_url = "https://www.example.com"
        partner1.target_url = example_url
        partner1.requested_access_duration = (
            True  # We don't want the ValidationError from requested_access_duration
        )
        partner1.save()
        partner2.target_url = example_url
        partner2.save()

        msg = check_for_target_url_duplication_and_generate_error_message(
            partner1, partner=True
        )
        self.assertIsNotNone(msg)
        self.assertIn(partner2.company_name, msg)

        self.assertRaises(ValidationError, partner1.clean)
        try:
            partner1.clean()
        except ValidationError as e:
            self.assertEqual([msg], e.messages)

        msg = check_for_target_url_duplication_and_generate_error_message(
            partner2, partner=True
        )
        self.assertIsNotNone(msg)
        # We only want the duplicate partner names to be shown,
        # not self.
        self.assertNotIn(partner2.company_name, msg)
        self.assertIn(partner1.company_name, msg)

        self.assertIsNotNone(msg)

    def test_user_instructions(self):
        partner1 = PartnerFactory(authorization_method=Partner.CODES)
        partner2 = PartnerFactory(authorization_method=Partner.CODES)

        user_instructions = "Wikimedia"
        partner1.user_instructions = user_instructions
        partner1.requested_access_duration = (
            True  # We don't want the ValidationError from requested_access_duration
        )
        partner2.user_instructions = ""
        partner2.requested_access_duration = (
            True  # We don't want the ValidationError from requested_access_duration
        )

        error_msg = "Partners with automatically sent messages require user instructions to be entered"

        # This partner should validate without errors.
        self.assertEqual(partner1.clean(), None)

        # This partner should fail validation.
        self.assertRaises(ValidationError, partner2.clean)
        try:
            partner2.clean()
        except ValidationError as e:
            # We're making sure that it fails because of a lack of user instructions, specifically.
            self.assertEqual([error_msg], e.messages)

    def test_for_target_url_not_empty_when_authorization_method_is_proxy_or_bundle(
        self,
    ):
        """
        When partner’s authorization method is PROXY or BUNDLE
        then leaving target_url empty should raise a ValidationError
        """
        message = "Proxy and Bundle partners require a target URL."

        # test for a partner with proxy authorization method
        partner1 = PartnerFactory(authorization_method=Partner.PROXY)
        partner1.requested_access_duration = (
            True  # We don't want the ValidationError from requested_access_duration
        )

        self.assertRaises(ValidationError, partner1.clean)
        try:
            partner1.save()
        except ValidationError as e:
            self.assertEqual([message], e.messages)

    def test_for_target_url_not_empty_when_authorization_method_is_proxy_or_bundle_2(
        self,
    ):
        """
        When partner’s authorization method is not PROXY or not BUNDLE
        then leaving target_url empty should not raise a ValidationError
        """
        partner2 = PartnerFactory(authorization_method=Partner.EMAIL)
        self.assertEqual(partner2.clean(), None)

    def test_create_tags_success(self):
        """
        Test to check that new tags are created correctly
        """
        partner4 = PartnerFactory()

        partner4.new_tags = {"tags": ["law_tag", "earth-sciences_tag"]}

        partner4.save()

    def test_create_tags_error(self):
        """
        Test to check that an invalid JSON is not saved in the new_tags
        """
        partner5 = PartnerFactory()

        message = "Error trying to insert a tag: please choose a tag from <a rel='noopener' target='_blank' href='https://github.com/WikipediaLibrary/TWLight/blob/production/locale/en/tag_names.json'>tag_names.json</a>."

        partner5.new_tags = {"tags": ["this_doesnt_exist_tag", "earth-sciences_tag"]}

        self.assertRaises(ValidationError, partner5.clean)

        try:
            partner5.clean()
        except ValidationError as e:
            self.assertEqual([message], e.messages)

    def test_create_tags_error2(self):
        """
        Test to check that an invalid JSON is not saved in the new_tags
        """
        partner5 = PartnerFactory()

        message = "Error trying to insert a tag: please choose a tag from <a rel='noopener' target='_blank' href='https://github.com/WikipediaLibrary/TWLight/blob/production/locale/en/tag_names.json'>tag_names.json</a>."

        partner5.new_tags = {
            "tags": ["law_tag", "earth-sciences_tag"],
            "other_key": "error",
        }

        self.assertRaises(ValidationError, partner5.clean)

        try:
            partner5.clean()
        except ValidationError as e:
            self.assertEqual([message], e.messages)

    def test_create_tags_error3(self):
        """
        Test to check that an empty JSON is not saved in the new_tags
        since saving a JSON null is not recommended
        https://docs.djangoproject.com/en/3.1/topics/db/queries/#storing-and-querying-for-none
        """
        partner6 = PartnerFactory()

        message = "Error trying to insert a tag: please choose a tag from <a rel='noopener' target='_blank' href='https://github.com/WikipediaLibrary/TWLight/blob/production/locale/en/tag_names.json'>tag_names.json</a>."

        partner6.new_tags = {}

        self.assertRaises(ValidationError, partner6.clean)

        try:
            partner6.clean()
        except ValidationError as e:
            self.assertEqual([message], e.messages)


class WaitlistBehaviorTests(TestCase):
    """
    Tests of user-visible behavior with respect to waitlist status. We're
    *not* testing particular HTML messages as those kinds of tests tend to be
    extremely brittle.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

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

    def test_toggle_available_to_waitlist_changes_application_waitlist_status(self):
        """
        Post to the toggle waitlist view set to make an AVAILABLE partner
        change to WAITLIST. By doing this waitlist_status of some applications
        under this partner will become True.
        """

        # Create needed objects
        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)
        UserProfileFactory(user=editor.user, terms_of_use=True)

        # Create a Partner and some applications for it
        partner = PartnerFactory(status=Partner.AVAILABLE)
        app1 = ApplicationFactory(partner=partner, status=Application.PENDING)
        app2 = ApplicationFactory(partner=partner, status=Application.QUESTION)
        app3 = ApplicationFactory(partner=partner, status=Application.APPROVED)
        app4 = ApplicationFactory(
            partner=partner, status=Application.SENT, sent_by=editor.user
        )

        # Set up request
        url = reverse("partners:toggle_waitlist", kwargs={"pk": partner.pk})
        request = RequestFactory().post(url)
        request.user = editor.user
        _ = PartnersToggleWaitlistView.as_view()(request, pk=partner.pk)
        partner.refresh_from_db()

        # Test partner status is changed to Waitlist
        self.assertEqual(partner.status, Partner.WAITLIST)

        # Test if waitlist_status is True for all applications
        # which are Pending or Under Discussion for this partner
        applications = Application.objects.filter(
            partner=partner, status__in=[Application.PENDING, Application.QUESTION]
        )
        for app in applications:
            self.assertEqual(app.waitlist_status, True)


class PartnerViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.partner = PartnerFactory()
        editor = EditorFactory()
        cls.user = UserFactory(editor=editor)
        cls.coordinator = UserFactory()
        cls.coordinator2 = UserFactory()

        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)
        coordinators.user_set.add(cls.coordinator2)

        cls.partner.coordinator = cls.coordinator
        cls.partner.save()

        cls.application = ApplicationFactory(
            partner=cls.partner,
            editor=editor,
            status=Application.SENT,
            sent_by=cls.coordinator,
        )

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

    def test_partner_views(self):
        partner = PartnerFactory()

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Designate the coordinator
        partner.coordinator = editor.user
        partner.save()

        # Creates applications for partner
        app1 = ApplicationFactory(partner=partner, status=Application.APPROVED)
        app2 = ApplicationFactory(partner=partner, status=Application.NOT_APPROVED)
        app3 = ApplicationFactory(
            partner=partner, status=Application.SENT, sent_by=editor.user
        )

        partner_detail_url = reverse("partners:detail", kwargs={"pk": partner.pk})
        response = self.client.get(partner_detail_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # check whether median_days is not None
        self.assertNotEqual(response.context["median_days"], None)


class CSVUploadTest(TestCase):  # Migrated from staff dashboard test
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        editor = EditorFactory()
        cls.user = editor.user

        cls.partner = PartnerFactory(
            status=Partner.WAITLIST,
            authorization_method=Partner.PROXY,
            accounts_available=10,
        )
        cls.partner1 = PartnerFactory(
            status=Partner.WAITLIST,
            authorization_method=Partner.PROXY,
            accounts_available=2,
        )

        cls.application = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=cls.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        cls.application1 = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=cls.partner1,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        cls.coordinator = UserFactory(username="coordinator")
        cls.coordinator.set_password("coordinator")
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)
        cls.coordinator.userprofile.terms_of_use = True
        cls.coordinator.userprofile.save()

        auth1 = Authorization.objects.create(
            user=cls.user, authorizer=cls.coordinator, date_expires=date.today()
        )
        auth1.partners.add(cls.partner)

        auth2 = Authorization.objects.create(
            user=EditorFactory().user,
            authorizer=cls.coordinator,
            date_expires=date.today(),
        )
        auth2.partners.add(cls.partner)

        auth3 = Authorization.objects.create(
            user=cls.user,
            authorizer=cls.coordinator,
            date_expires=date.today() + timedelta(days=random.randint(1, 5)),
        )
        auth3.partners.add(cls.partner1)

        auth4 = Authorization.objects.create(
            user=EditorFactory().user,
            authorizer=cls.coordinator,
            date_expires=date.today() + timedelta(days=random.randint(1, 5)),
        )
        auth4.partners.add(cls.partner1)

        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.message_patcher.stop()

    def test_auto_disable_waitlist_command(self):
        self.assertEqual(self.partner.status, Partner.WAITLIST)
        self.assertEqual(self.partner1.status, Partner.WAITLIST)

        call_command("proxy_waitlist_disable")

        self.partner.refresh_from_db()
        self.assertEqual(self.partner.status, Partner.AVAILABLE)
        # No change should've been made to the partner with zero accounts available
        self.partner1.refresh_from_db()
        self.assertEqual(self.partner1.status, Partner.WAITLIST)


class BundlePartnerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        cls.bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)
        cls.proxy_partner_1 = PartnerFactory(authorization_method=Partner.PROXY)
        cls.email_partner_1 = PartnerFactory(authorization_method=Partner.EMAIL)
        cls.bundle_partner_3 = PartnerFactory(
            authorization_method=Partner.BUNDLE, status=Partner.NOT_AVAILABLE
        )

        cls.editor = EditorFactory()
        cls.editor.wp_bundle_eligible = True
        cls.editor.save()

    def test_switching_partner_to_bundle_updates_auths(self):
        """
        When a partner switches from a non-Bundle authorization
        method to Bundle, existing bundle authorizations
        should be updated to include it.
        """
        # This should create an authorization linked to
        # bundle partners.
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        self.proxy_partner_1.authorization_method = Partner.BUNDLE
        self.proxy_partner_1.save()

        self.assertEqual(bundle_authorization.first().partners.count(), 3)

    def test_switching_partner_from_bundle_updates_auths(self):
        """
        When a partner switches from the Bundle authorization
        method to non-Bundle, existing bundle authorizations
        should be updated to remove it.
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        self.bundle_partner_1.authorization_method = Partner.PROXY
        self.bundle_partner_1.save()

        self.assertEqual(bundle_authorization.first().partners.count(), 1)

    def test_making_bundle_partner_available_updates_auths(self):
        """
        When a partner is made available after being marked
        not available, existing bundle authorizations
        should be updated to add it.
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        self.bundle_partner_3.status = Partner.AVAILABLE
        self.bundle_partner_3.save()

        self.assertEqual(bundle_authorization.first().partners.count(), 3)

    def test_making_bundle_partner_not_available_updates_auths(self):
        """
        When a partner is marked as not available, existing bundle
        authorizations should be updated to add it.
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        self.bundle_partner_1.status = Partner.NOT_AVAILABLE
        self.bundle_partner_1.save()

        self.assertEqual(bundle_authorization.first().partners.count(), 1)

    def test_making_proxy_partner_not_available_doesnt_update_bundle_auths(self):
        """
        Changing the availability of a PROXY partner should make no
        changes to bundle auths
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        self.proxy_partner_1.status = Partner.NOT_AVAILABLE
        self.proxy_partner_1.save()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

    def test_making_proxy_partner_email_doesnt_update_bundle_auths(self):
        """
        Changing the authorization method of a PROXY partner
        to a non-bundle authorization should not make any changes
        to bundle auths
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        self.proxy_partner_1.authorization_method = Partner.EMAIL
        self.proxy_partner_1.save()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

    def test_creating_bundle_partner_updates_bundle_auths(self):
        """
        Creating a new partner with the BUNDLE authorization method
        immediately should add to existing Bundle authorizations.
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        _ = PartnerFactory(
            authorization_method=Partner.BUNDLE, status=Partner.AVAILABLE
        )

        self.assertEqual(bundle_authorization.first().partners.count(), 3)

    def test_creating_not_available_bundle_partner_doesnt_update_bundle_auths(self):
        """
        Creating a new partner with the BUNDLE authorization method
        but NOT_AVAILABLE status should not change existing auths
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        _ = PartnerFactory(
            authorization_method=Partner.BUNDLE, status=Partner.NOT_AVAILABLE
        )

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

    def test_creating_proxy_partner_doesnt_update_bundle_auths(self):
        """
        Creating a new partner with the PROXY authorization method
        should make no change to existing Bundle authorizations
        """
        self.editor.update_bundle_authorization()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

        _ = PartnerFactory(authorization_method=Partner.PROXY, status=Partner.AVAILABLE)

        self.assertEqual(bundle_authorization.first().partners.count(), 2)

    def test_switching_partner_to_bundle_deletes_previous_auths(self):
        """
        Users may have previously had an authorization to a partner that
        we switch to Bundle. When switching a partner to Bundle, they
        should be deleted and we should only have a single Bundle auth.
        """
        # Before we create the user's Bundle authorizations, let's
        # give them an authorization to the Proxy partner.

        application = ApplicationFactory(
            partner=self.proxy_partner_1, editor=self.editor, status=Application.PENDING
        )

        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        application.status = Application.APPROVED
        application.sent_by = coordinator.user
        application.save()

        # We should now have an auth for this user to this partner
        try:
            authorization = Authorization.objects.get(
                user=self.editor.user,
                partners=Partner.objects.get(pk=self.proxy_partner_1.pk),
            )
        except Authorization.DoesNotExist:
            self.fail("Authorization wasn't created in the first place.")

        self.editor.update_bundle_authorization()

        self.proxy_partner_1.authorization_method = Partner.BUNDLE
        self.proxy_partner_1.save()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        # Ultimately we should have one Bundle authorization
        self.assertEqual(bundle_authorization.count(), 1)

    def test_switching_partner_to_bundle_doesnt_create_duplicate_auths(self):
        """
        When switching a partner from available to non-available status
        and switched to Bundle in the same query, then
        1. It should not create duplicate Bundle Authorization for the user.
        2. It should delete previous Authorizations of Partner since it
        is moved to Bundle now.
        3. It should not be returned in any Bundle Authorization currently since
        it is in a non-available status right now. So Authorizations must not be
        created for it.
        4. Once it is moved to Available again Bundle Authorizations must get
        create for it automatically.
        """
        # Before we create the user's Bundle authorizations, let's
        # give them an authorization to the Proxy partner.

        application = ApplicationFactory(
            partner=self.email_partner_1, editor=self.editor, status=Application.PENDING
        )

        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        application.status = Application.SENT
        application.sent_by = coordinator.user
        application.save()

        # We should now have an auth for this user to this partner
        try:
            authorization = Authorization.objects.get(
                user=self.editor.user,
                partners=Partner.objects.get(pk=self.email_partner_1.pk),
            )
        except Authorization.DoesNotExist:
            self.fail("Authorization wasn't created in the first place.")

        self.editor.update_bundle_authorization()

        self.email_partner_1.authorization_method = Partner.BUNDLE
        self.email_partner_1.status = Partner.WAITLIST
        self.email_partner_1.save()

        bundle_authorization = Authorization.objects.filter(
            user=self.editor.user, partners__authorization_method=Partner.BUNDLE
        ).distinct()

        # Ultimately we should have one Bundle authorization
        # New bundle partner should not create duplicate
        # Bundle Authorization for the user
        self.assertEqual(bundle_authorization.count(), 1)

        email_partner_authorizations = Authorization.objects.filter(
            partners__pk=self.email_partner_1.pk
        )
        # All previous Authorizations of Email Partner must be deleted
        # since it is moved to Bundle now.
        self.assertEqual(email_partner_authorizations.exists(), False)

        all_bundle_authorizations = get_all_bundle_authorizations()

        # Parnter should not be in Bundle Authorization currently since
        # it is in a non-available status right now. So Authorizations must not be
        # created for it.
        for authorization in all_bundle_authorizations:
            if self.email_partner_1 in authorization.partners.all():
                self.fail("Waitlisted bundle partner having Bundle Authorization")

        # If the partner is set to available now, it should get added to all Bundle
        # Authorizations Automatically
        self.email_partner_1.status = Partner.AVAILABLE
        self.email_partner_1.save()

        for authorization in all_bundle_authorizations:
            if self.email_partner_1 not in authorization.partners.all():
                self.fail(
                    "Available bundle partner not present in Bundle Authorization"
                )


class PartnerSuggestionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.suggestion = SuggestionFactory()
        cls.suggestion_to_delete = SuggestionFactory()
        cls.editor = EditorCraftRoom(cls, Terms=True, Coordinator=True)
        cls.upvoter = EditorCraftRoom(cls, Terms=True)
        cls.user = UserFactory(editor=cls.editor)
        cls.suggestion.author = cls.editor.user
        cls.suggestion_to_delete.author = cls.editor.user

        cls.suggestion.upvoted_users.add(cls.editor.user)
        cls.suggestion_to_delete.upvoted_users.add(cls.editor.user)
        cls.suggestion.save()
        cls.suggestion_to_delete.save()

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.message_patcher.stop()

    def test_partner_suggestion_view_get(self):
        """
        Tests that getting the suggested partners works properly
        """
        suggestion_url = reverse("suggest")

        factory = RequestFactory()
        request = factory.get(suggestion_url)
        request.user = self.user

        response = PartnerSuggestionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.suggestion.company_url)

    def test_partner_suggestion_view_post(self):
        """
        Tests that adding a new partner suggestion works properly
        """
        suggestion_url = reverse("suggest")

        new_suggested_partner = {
            "suggested_company_name": "Company",
            "company_url": "www.testing123.com",
            "author": self.user,
        }
        factory = RequestFactory()
        request = factory.post(suggestion_url, new_suggested_partner)
        request.user = self.user

        response = PartnerSuggestionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, new_suggested_partner["suggested_company_name"])
        self.assertContains(response, new_suggested_partner["company_url"])

    def test_partner_suggestion_upvote_view(self):
        """
        Tests that upvoting a partner suggestion works properly
        """
        suggestion_url = reverse("upvote", kwargs={"pk": self.suggestion.pk})

        suggestion_before_upvote = Suggestion.objects.get(pk=self.suggestion.pk)
        self.assertEqual(suggestion_before_upvote.upvoted_users.count(), 1)

        # Create a coordinator with a test client session
        EditorCraftRoom(self, Terms=True, Coordinator=True)
        request = self.client.get(path=suggestion_url, follow=True)

        suggestion = Suggestion.objects.get(pk=self.suggestion.pk)

        self.assertEqual(request.status_code, 200)
        self.assertEqual(suggestion.upvoted_users.count(), 2)

    def test_partner_suggestion_delete_view(self):
        """
        Tests that deleting a partner suggestion works properly
        """
        suggestion_url = reverse(
            "suggest-delete", kwargs={"pk": self.suggestion_to_delete.pk}
        )
        # Create a coordinator with a test client session
        EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Checking that the suggestion hasn't been deleted yet
        self.assertEquals(Suggestion.objects.count(), 2)

        response = self.client.delete(path=suggestion_url, follow=True)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(Suggestion.objects.count(), 1)


class SuggestionMergeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.main_suggestion = SuggestionFactory(company_url="www.testingMerged1234.com")
        cls.merge_suggestion_url = reverse("suggest-merge")

        # Manually setting up with EditorFactory since we don't need a client session yet
        cls.coordinator = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator.user)
        cls.staff = EditorFactory()
        cls.staff.user.is_staff = True
        coordinators.user_set.add(cls.staff.user)
        cls.editor = EditorFactory()

        cls.upvoters_or_authors = [cls.editor, cls.coordinator]
        cls.main_suggestion.author = cls.coordinator.user
        cls.main_suggestion.upvoted_users.add(cls.coordinator.user)
        cls.main_suggestion.save()

        cls.suggestion_merge_count = 5

        cls.company_urls = ["www.testing123.com", "www.testingMerge123.com"]
        cls.secondary_suggestions = [
            SuggestionFactory(company_url=random.choice(cls.company_urls))
            for _ in range(cls.suggestion_merge_count)
        ]
        for suggestion in cls.secondary_suggestions:
            upvoter_or_author = random.choice(cls.upvoters_or_authors)
            suggestion.author = upvoter_or_author.user
            suggestion.upvoted_users.add(upvoter_or_author.user)
            suggestion.save()
        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.message_patcher.stop()

    def test_partner_suggestion_view_staff_only(self):
        """
        Tests that getting the suggested partners page for merge works only for staff.
        """

        factory = RequestFactory()
        request = factory.get(self.merge_suggestion_url)
        request.user = self.editor.user
        with self.assertRaises(PermissionDenied):
            response = SuggestionMergeView.as_view()(request)
        request.user = self.coordinator.user
        with self.assertRaises(PermissionDenied):
            response = SuggestionMergeView.as_view()(request)
        request.user = self.staff.user
        response = SuggestionMergeView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_merge_partner_suggestion_view_post(self):
        """
        Tests that merging a partner suggestion works properly, with upvotes too getting merged properly
        """

        # setup suggestion pk form data
        secondary_suggestions_pks = []
        for suggestion in self.secondary_suggestions:
            secondary_suggestions_pks.append(suggestion.pk)
        merge_suggestion_data = {
            "main_suggestion": self.main_suggestion.pk,
            "secondary_suggestions": secondary_suggestions_pks,
        }

        # Start a staff test client session
        EditorCraftRoom(self, Terms=True, Coordinator=True, editor=self.staff)

        # Submit form
        response = self.client.post(
            self.merge_suggestion_url, merge_suggestion_data, follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify state after submission:
        response = self.client.get(self.merge_suggestion_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # secondary_suggestions should be absent
        for suggestion in self.secondary_suggestions:
            self.assertNotContains(response, suggestion.company_url)
            self.assertNotContains(response, suggestion.suggested_company_name)

        # merged_suggestion should be present
        merged_suggestion = Suggestion.objects.get(pk=self.main_suggestion.pk)
        self.assertContains(response, merged_suggestion.suggested_company_name)
        self.assertContains(response, merged_suggestion.company_url)

        # upvotes should be combined
        self.assertEqual(merged_suggestion.upvoted_users.count(), 2)


class PartnerFilesTest(TestCase):
    def test_partner_files_json_valid(self):
        twlight_home = settings.TWLIGHT_HOME
        locale_dir = "{twlight_home}/locale".format(twlight_home=twlight_home)
        # Using listdir for directory traversal instead of os.walk because
        # we only need to traverse the first level of the locale/ directory
        for dir in os.listdir(locale_dir):
            language_dir = os.path.join(locale_dir, dir)
            # Check if the element within local/ directory is also a directory
            # A directory here represents a language in the application
            if os.path.isdir(language_dir):
                partner_file = os.path.join(locale_dir, "partner_descriptions.json")
                if os.path.isfile(partner_file):
                    # Validate json with json-schema
                    with open(partner_file, "r") as partner_file:
                        partner_json = json.load(partner_file)
                        validate(
                            instance=partner_json,
                            schema=get_partner_description_json_schema(),
                        )
