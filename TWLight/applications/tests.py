# -*- coding: utf-8 -*-
import html
import random
import urllib
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from itertools import chain
from unittest.mock import patch
import reversion
from urllib.parse import urlparse

from django import forms
from django_comments import get_form_target
from django_comments.models import Comment
from django_comments.signals import comment_was_posted
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.core.management import call_command
from django.db import models
from django.http import Http404
from django.test import TestCase, Client, RequestFactory
from django.utils.html import escape

from TWLight.helpers import site_id
from TWLight.resources.models import Partner, Stream, AccessCode
from TWLight.resources.factories import PartnerFactory, StreamFactory
from TWLight.resources.tests import EditorCraftRoom
from TWLight.users.factories import EditorFactory, UserFactory
from TWLight.users.groups import get_coordinators, get_restricted
from TWLight.users.models import Authorization, Editor

from . import views
from .helpers import (
    USER_FORM_FIELDS,
    PARTNER_FORM_OPTIONAL_FIELDS,
    FIELD_TYPES,
    SPECIFIC_STREAM,
    SPECIFIC_TITLE,
    AGREEMENT_WITH_TERMS_OF_USE,
    REAL_NAME,
    COUNTRY_OF_RESIDENCE,
    OCCUPATION,
    AFFILIATION,
    ACCOUNT_EMAIL,
    get_output_for_application,
    count_valid_authorizations,
)
from .factories import ApplicationFactory
from .forms import BaseApplicationForm
from .models import Application


class SendCoordinatorRemindersTest(TestCase):
    """
    Stub of a test for the send_coordinator_reminders command.
    Currently we're not actually checking for any desired/undesired behavior,
    we're just verifying that the command can be executed without throwing an
    error. 
    """

    def test_command_output(self):
        call_command("send_coordinator_reminders")


class SynchronizeFieldsTest(TestCase):
    """
    There are four distinct places we record facts about what types of extra
    information Partners might request in Applications:
    * resources.models.Partner (checks which information this Partner requires)
    * applications.models.Application (records the actual information supplied
      by the user, specific to an application for a given partner resource)
    * users.models.Editor (records the actual information supplied by the user,
      specific to that user but not to any one partner application)
    * applications.helpers (the list of information partners might require,
      plus a mapping from each type of information to the type of form field
      suitable for containing it)

    Ideally we would have a single source of truth (in applications.helpers),
    but we have to actually define the database schemata for Partner and
    Application in a fixed way. Alas!

    In lieu of a single source of truth, we have a test case here which checks
    the following:

    * does every optional partner and optional user data field correspond to an
      attribute of Partner? (That is, does Partner actually let us record
      whether a given partner wishes us to harvest that optional datum or not.)
    * are all the optional partner fields reflected in Application? (That is,
      can we actually record them?)
    * are all the optional user data fields reflected in User? (Again, can we
      record them?)
    * for each data field, do we have a form field type (allowing us to
      generate forms for harvesting the data)?
    * does that form field type match the corresponding field on Editor or
      Application?

    The purpose of this test is to save us from ourselves. To wit:

    If future Partners require types of information not reflected in our
    current code, we need to add that information to several places. This test
    ensures that all of those places are kept in sync - that is, that we update
    all the things we need to update, if we update any of them.
    """

    def _get_all_field_names(self, model):
        # See https://docs.djangoproject.com/en/1.10/ref/models/meta/#migrating-from-the-old-api.
        return list(
            set(
                chain.from_iterable(
                    (field.name, field.attname)
                    if hasattr(field, "attname")
                    else (field.name,)
                    for field in model._meta.get_fields()
                    if not (field.many_to_one and field.related_model is None)
                )
            )
        )

    def test_user_form_fields_reflected_in_partner(self):
        """
        The Partner model should let each instance indicate whether it requires
        the optional user data.
        """
        for field in USER_FORM_FIELDS:
            self.assertTrue(field in self._get_all_field_names(Partner))

    def test_optional_partner_form_fields_reflected_in_partner(self):
        """
        The Partner model should let each instance indicate whether it requires
        the optional partner data.
        """
        for field in PARTNER_FORM_OPTIONAL_FIELDS:
            self.assertTrue(field in self._get_all_field_names(Partner))

    def test_partner_optional_fields_are_boolean(self):
        """
        The optional user and partner data fields on Partner should be
        booleans, allowing each instance to indicate whether (True/False) it
        requires that data.
        """
        optional_fields = USER_FORM_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS
        for field in optional_fields:
            self.assertTrue(
                isinstance(Partner._meta.get_field(field), models.BooleanField)
            )

    def test_optional_partner_form_fields_reflected_in_application(self):
        """
        The Application model should let each instance record the optional
        partner data, as needed.
        """
        for field in PARTNER_FORM_OPTIONAL_FIELDS:
            self.assertTrue(field in self._get_all_field_names(Application))

    def test_application_optional_fields_match_field_type(self):
        """
        The optional partner-specific data fields on Application should
        correspond to the FIELD_TYPES used on the form. Additionally, each
        should allow blank=True (since not all instances require all data),
        except for BooleanFields, which should default False (i.e. they should
        default to not requiring the data).
        """
        for field in PARTNER_FORM_OPTIONAL_FIELDS:
            # Ensure Application fields allow for empty data.
            if not isinstance(Application._meta.get_field(field), models.BooleanField):
                self.assertTrue(Application._meta.get_field(field).blank)
            else:
                self.assertFalse(Application._meta.get_field(field).default)

            # Make sure the form fields we're using match what the model fields
            # can record.
            modelfield = Application._meta.get_field(field)
            formfield = modelfield.formfield()

            # While we simply use the ChoiceField for requested_access_duration field in the form, the model makes use
            # of the TypedChoiceField, triggering a mismatch. We'll get around this by separately testing the fields.
            if field == "requested_access_duration":
                self.assertEqual(type(formfield), forms.TypedChoiceField)
                self.assertEqual(type(FIELD_TYPES[field]), forms.ChoiceField)
                break

            self.assertEqual(type(formfield), type(FIELD_TYPES[field]))

    def test_user_form_fields_reflected_in_editor(self):
        """
        The Editor model should let each instance record the user data, as
        needed.
        """
        for field in USER_FORM_FIELDS:
            self.assertTrue(field in self._get_all_field_names(Editor))

    def test_editor_optional_fields_match_field_type(self):
        """
        The optional user data fields on Editor should correspond to the
        FIELD_TYPES used on the application form. Additionally, each should
        allow blank=True (since not all instances require all data), except for
        BooleanFields, which should default False (i.e. they should default to
        not requiring the data).
        """
        for field in USER_FORM_FIELDS:
            # Ensure Editor fields allow for empty data.
            if not isinstance(Editor._meta.get_field(field), models.BooleanField):
                self.assertTrue(Editor._meta.get_field(field).blank)
            else:
                self.assertFalse(Editor._meta.get_field(field).default)

            # Make sure the form fields we're using match what the model fields
            # can record.
            modelfield = Editor._meta.get_field(field)
            formfield = modelfield.formfield()

            self.assertEqual(type(formfield), type(FIELD_TYPES[field]))

    def test_application_output_1(self):
        """
        We also rely on our field names to generate data to send to partners,
        and need to ensure that get_output_for_application provides all needed
        data (but no unneeded data).

        Case 1, we'll test an application where a partner requires all of the
        optional fields.
        """
        editor = EditorFactory()
        setattr(editor, REAL_NAME, "Alice")
        setattr(editor, COUNTRY_OF_RESIDENCE, "Holy Roman Empire")
        setattr(editor, OCCUPATION, "Dog surfing instructor")
        setattr(editor, AFFILIATION, "The Long Now Foundation")
        setattr(editor, "wp_username", "wp_alice")
        setattr(editor, "email", "alice@example.com")
        editor.save()

        partner = Partner()
        for field in USER_FORM_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS:
            setattr(partner, field, True)
        partner.terms_of_use = "https://example.com/terms"
        partner.registration_url = "https://example.com/register"
        partner.save()

        stream = Stream()
        stream.partner = partner
        stream.name = "Stuff and things"
        stream.save()

        app = ApplicationFactory(
            status=Application.APPROVED,
            partner=partner,
            editor=editor,
            rationale="just because",
            comments="nope",
        )
        setattr(app, AGREEMENT_WITH_TERMS_OF_USE, True)
        setattr(app, ACCOUNT_EMAIL, "alice@example.com")
        setattr(app, SPECIFIC_STREAM, stream)
        setattr(app, SPECIFIC_TITLE, "Alice in Wonderland")
        app.save()

        app.refresh_from_db()

        output = get_output_for_application(app)
        self.assertEqual(output[REAL_NAME]["data"], "Alice")
        self.assertEqual(output[COUNTRY_OF_RESIDENCE]["data"], "Holy Roman Empire")
        self.assertEqual(output[OCCUPATION]["data"], "Dog surfing instructor")
        self.assertEqual(output[AFFILIATION]["data"], "The Long Now Foundation")
        self.assertEqual(output[SPECIFIC_STREAM]["data"], stream)
        self.assertEqual(output[SPECIFIC_TITLE]["data"], "Alice in Wonderland")
        self.assertEqual(output["Email"]["data"], "alice@example.com")
        self.assertEqual(output[AGREEMENT_WITH_TERMS_OF_USE]["data"], True)
        self.assertEqual(output[ACCOUNT_EMAIL]["data"], "alice@example.com")

        # Make sure that in enumerating the keys we didn't miss any (e.g. if
        # the codebase changes).
        self.assertEqual(9, len(list(output.keys())))

    def test_application_output_2(self):
        """
        Case 2, we'll test an application where a partner requires none of the
        optional fields.
        """
        editor = EditorFactory()
        setattr(editor, "wp_username", "wp_alice")
        setattr(editor, "email", "alice@example.com")
        editor.save()

        partner = Partner()
        for field in USER_FORM_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS:
            setattr(partner, field, False)
        partner.save()

        app = ApplicationFactory(
            status=Application.APPROVED,
            partner=partner,
            editor=editor,
            rationale="just because",
            comments="nope",
        )
        app.agreement_with_terms_of_use = False
        app.save()

        app.refresh_from_db()

        output = get_output_for_application(app)
        self.assertEqual(output["Email"]["data"], "alice@example.com")

        # Make sure that in enumerating the keys we didn't miss any (e.g. if
        # the codebase changes).
        self.assertEqual(1, len(list(output.keys())))

    def test_application_output_3(self):
        """
        Case 3, we'll test an application where a partner requires some but not
        all of the optional fields.
        """
        editor = EditorFactory()
        setattr(editor, REAL_NAME, "Alice")
        setattr(editor, COUNTRY_OF_RESIDENCE, "Holy Roman Empire")
        setattr(editor, OCCUPATION, "Dog surfing instructor")
        setattr(editor, AFFILIATION, "The Long Now Foundation")
        setattr(editor, "wp_username", "wp_alice")
        setattr(editor, "email", "alice@example.com")
        editor.save()

        partner = Partner()
        for field in PARTNER_FORM_OPTIONAL_FIELDS:
            setattr(partner, field, False)
        for field in USER_FORM_FIELDS:
            setattr(partner, field, True)
        partner.save()

        app = ApplicationFactory(
            status=Application.APPROVED,
            partner=partner,
            editor=editor,
            rationale="just because",
            comments="nope",
        )
        app.agreement_with_terms_of_use = False
        app.save()

        app.refresh_from_db()

        output = get_output_for_application(app)
        self.assertEqual(output[REAL_NAME]["data"], "Alice")
        self.assertEqual(output[COUNTRY_OF_RESIDENCE]["data"], "Holy Roman Empire")
        self.assertEqual(output[OCCUPATION]["data"], "Dog surfing instructor")
        self.assertEqual(output[AFFILIATION]["data"], "The Long Now Foundation")
        self.assertEqual(output["Email"]["data"], "alice@example.com")

        # Make sure that in enumerating the keys we didn't miss any (e.g. if
        # the codebase changes).
        self.assertEqual(5, len(list(output.keys())))


class BaseApplicationViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseApplicationViewTest, cls).setUpClass()
        cls.client = Client()

        # Note: not an Editor.
        cls.base_user = UserFactory(username="base_user")
        cls.base_user.set_password("base_user")
        cls.base_user.userprofile.terms_of_use = True
        cls.base_user.userprofile.save()

        cls.editor = UserFactory(username="editor")
        EditorFactory(user=cls.editor)
        cls.editor.set_password("editor")
        cls.editor.userprofile.terms_of_use = True
        cls.editor.userprofile.save()

        cls.editor2 = UserFactory(username="editor2")
        EditorFactory(user=cls.editor2)
        cls.editor2.set_password("editor2")
        cls.editor2.userprofile.terms_of_use = True
        cls.editor2.userprofile.save()

        cls.coordinator = UserFactory(username="coordinator")
        cls.coordinator.set_password("coordinator")
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)
        cls.coordinator.userprofile.terms_of_use = True
        cls.coordinator.userprofile.save()

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super(BaseApplicationViewTest, cls).tearDownClass()
        cls.base_user.delete()
        cls.editor.delete()
        cls.editor2.delete()
        cls.coordinator.delete()

        cls.message_patcher.stop()

    def tearDown(self):
        super(BaseApplicationViewTest, self).tearDown()
        for partner in Partner.objects.all():
            partner.delete()

    def _get_isolated_view(self, view_class, user=None):
        """
        Get an instance of the view that we can test in isolation, without
        requiring Client().
        """
        if not user:
            user = self.editor

        request = RequestFactory().get(self.url)
        view = view_class()
        view.request = request
        view.request.user = user
        return view


class RequestApplicationTest(BaseApplicationViewTest):
    @classmethod
    def setUpClass(cls):
        super(RequestApplicationTest, cls).setUpClass()
        cls.url = reverse("applications:request")

    def _get_request_with_session(self, data):
        """
        Why the song-and-dance with middleware? Well. RequestFactory() lets us
        add a user to the request, e.g. in order to pass our ToURequired test,
        but doesn't let us access the session by default; Client() lets us see
        the session, but not add a user to the request. We need to pass our
        access test *and* see the session, so we need to:
            * use RequestFactory() to add a user to the request
            * invoke SessionMiddleware to bring the session into being
            * actually generate the response, so that form_valid is invoked,
              since that is where the session key is added

        If you were getting the sense that class-based views are sometimes
        hostile to unit testing, you were right.
        """

        request = RequestFactory().post(self.url, data=data, follow=True)
        request.user = self.editor
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()

        _ = views.RequestApplicationView.as_view()(request)
        return request

    def test_authorization(self):
        """
        Only Editors should be able to request access to applications.
        """
        # An anonymous user is prompted to login.
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = AnonymousUser()

        # Make sure there's a session key - otherwise we'll get redirected to
        # /applications/request before we hit the login test
        p1 = PartnerFactory()
        request.session = {views.PARTNERS_SESSION_KEY: [p1.pk]}

        with self.assertRaises(PermissionDenied):
            _ = views.RequestApplicationView.as_view()(request)

        # A user who is not a WP editor does not have access.
        request.user = self.base_user
        with self.assertRaises(PermissionDenied):
            _ = views.RequestApplicationView.as_view()(request)

        # An editor may see the page.
        request.user = self.editor

        # Note: No PermissionDenied raised!
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_email_required_or_superuser(self):
        """
        Only users with emails on file (or superusers) should be allowed to see
        this view - anyone else should be redirected through the email change
        page.
        """
        # Set up request.
        factory = RequestFactory()
        request = factory.get(self.url)
        p1 = PartnerFactory()
        request.session = {views.PARTNERS_SESSION_KEY: [p1.pk]}
        user = UserFactory()
        user.userprofile.terms_of_use = True
        user.userprofile.save()
        _ = EditorFactory(user=user)
        request.user = user

        # Case 1: no email; access should be denied.
        user.email = ""
        user.save()
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)

        # Case 2: user has email; access should be allowed.
        user.email = "foo@bar.com"
        user.save()
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        # Case 3: user is superuser; access should be allowed.
        user.is_superuser = True
        user.save()
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        # Case 4: user is still superuser; even without email access should be
        # allowed.
        user.email = ""
        user.save()
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_form_class(self):
        """
        Ensure that the form created by RequestApplicationView has one
        BooleanField per Partner in the database, to allow Editors to select
        the ones they wish to apply for.
        """
        view = self._get_isolated_view(views.RequestApplicationView)

        # Make sure we've zeroed out the Partners, so we have the number we
        # expect.
        for partner in Partner.objects.all():
            partner.delete()

        # Check that it works with only one Partner in the database.
        partner = PartnerFactory()

        form_class = view.get_form_class()
        form = form_class()
        self.assertEqual(len(form.fields), 1)

        fieldkey = "partner_{id}".format(id=partner.id)
        self.assertIn(fieldkey, form.fields)
        assert isinstance(form.fields[fieldkey], forms.BooleanField)

        # Add Partners and see how many form fields there are. We'll assume
        # that they're all of the correct type, having tested that the first
        # one is.
        _ = PartnerFactory()
        _ = PartnerFactory()
        _ = PartnerFactory()

        form_class = view.get_form_class()
        form = form_class()
        self.assertEqual(len(form.fields), 4)

        # Add BUNDLE partners and ensure the form fields remain intact
        PartnerFactory(authorization_method=Partner.BUNDLE)
        form_class = view.get_form_class()
        form = form_class()
        self.assertEqual(len(form.fields), 4)

    def test_empty_post(self):
        """
        Ensure that, if users don't select any Partners:
        1) they end up back on the request page;
        2) the session key is empty.
        """

        # First, create some partners, so the form isn't null.
        _ = PartnerFactory()
        _ = PartnerFactory()

        # Now check our docstring expectations.

        # We need to use the RequestFactory and not the client here because we
        # need to be able to set a user attribute on the request; otherwise
        # the view_mixins fail because they all see AnonymousUser, regardless
        # of the login cookie.

        factory = RequestFactory()
        request = factory.post(self.url, data={})
        request.user = self.editor
        request.session = {}
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.url, self.url)

    def test_valid_form_redirects(self):
        """
        Users who submit a valid form end up on the application page.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        data = {
            "partner_{id}".format(id=p1.id): True,
            "partner_{id}".format(id=p2.id): False,
        }

        factory = RequestFactory()
        request = factory.post(self.url, data=data)
        request.user = self.editor
        request.session = {}
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.url, reverse("applications:apply"))

    def test_valid_form_writes_session_key(self):
        """
        Users who submit a valid form generate a matching session key.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        data = {
            "partner_{id}".format(id=p1.id): True,
            "partner_{id}".format(id=p2.id): False,
        }
        request = self._get_request_with_session(data)
        self.assertEqual(request.session[views.PARTNERS_SESSION_KEY], [p1.id])

        data = {
            "partner_{id}".format(id=p1.id): False,
            "partner_{id}".format(id=p2.id): True,
        }
        request = self._get_request_with_session(data)
        self.assertEqual(request.session[views.PARTNERS_SESSION_KEY], [p2.id])

        data = {
            "partner_{id}".format(id=p1.id): True,
            "partner_{id}".format(id=p2.id): True,
        }
        request = self._get_request_with_session(data)

        # Since we don't care which order the IDs are in, but list comparison
        # is sensitive to order, let's check first that both lists have the
        # same elements, and second that they are of the same length.
        self.assertEqual(
            set(request.session[views.PARTNERS_SESSION_KEY]), {p2.id, p1.id}
        )
        self.assertEqual(
            len(request.session[views.PARTNERS_SESSION_KEY]), len([p2.id, p1.id])
        )

    def test_bundle_partner_in_form_data(self):
        """
        Building upon the previous test function, this tests for
        the appropriate handling of BUNDLE partners in the posted
        data (they shouldn't get added to the session key.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        data = {
            "partner_{id}".format(id=p1.id): True,
            "partner_{id}".format(id=p2.id): True,
        }
        request = self._get_request_with_session(data)
        self.assertEqual(request.session[views.PARTNERS_SESSION_KEY], [p1.id])


class SubmitApplicationTest(BaseApplicationViewTest):
    @classmethod
    def setUpClass(cls):
        super(SubmitApplicationTest, cls).setUpClass()
        cls.url = reverse("applications:apply")

    def tearDown(self):
        super(SubmitApplicationTest, self).tearDown()
        for partner in Partner.objects.all():
            partner.delete()

    def test_authorization(self):
        """
        Only Editors should be able to apply for access.
        """
        # An anonymous user is prompted to login.
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = AnonymousUser()

        # Make sure there's a session key - otherwise we'll get redirected to
        # /applications/request before we hit the login test
        p1 = PartnerFactory()
        request.session = {views.PARTNERS_SESSION_KEY: [p1.pk]}

        with self.assertRaises(PermissionDenied):
            _ = views.SubmitApplicationView.as_view()(request)

        # A user who is not a WP editor does not have access.
        factory = RequestFactory()

        request.user = self.base_user
        with self.assertRaises(PermissionDenied):
            _ = views.SubmitApplicationView.as_view()(request)

        # An editor may see the page.
        request.user = self.editor
        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_data_processing_required(self):
        """
        If users have requested a restriction on the processing of
        their data, they should not be allowed to apply for access.
        """
        # Set up request.
        factory = RequestFactory()
        request = factory.get(self.url)
        p1 = PartnerFactory()
        request.session = {views.PARTNERS_SESSION_KEY: [p1.pk]}
        user = UserFactory()
        user.userprofile.terms_of_use = True
        user.userprofile.save()
        _ = EditorFactory(user=user)
        request.user = user

        restricted = get_restricted()
        user.groups.add(restricted)
        user.save()

        with self.assertRaises(PermissionDenied):
            _ = views.SubmitApplicationView.as_view()(request)

    def test_missing_session_key(self):
        """
        If the PARTNERS_SESSION_KEY is missing, the view should redirect to
        RequestApplicationView.
        """

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        session = self.client.session
        if views.PARTNERS_SESSION_KEY in list(session.keys()):
            del session[views.PARTNERS_SESSION_KEY]

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        response_path = urlparse(response.url).path
        self.assertEqual(response_path, reverse("applications:request"))

    def test_empty_session_key(self):
        """
        If the PARTNERS_SESSION_KEY is an empty list, the view should redirect
        to RequestApplicationView.
        """
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.editor
        request.session = {views.PARTNERS_SESSION_KEY: []}

        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("applications:request"))

    def test_invalid_session_data(self):
        """
        If the PARTNERS_SESSION_KEY is not a list of valid pks of Partners, the
        view should redirect to RequestApplicationView.
        """
        _ = PartnerFactory()

        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.editor

        # Invalid pk: not an integer
        request.session = {views.PARTNERS_SESSION_KEY: ["cats"]}
        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("applications:request"))

        # Invalid pk: no such Partner
        self.assertEqual(Partner.objects.filter(pk=4500).count(), 0)

        request.session[views.PARTNERS_SESSION_KEY] = [1, 4500]
        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("applications:request"))

    def test_valid_session_data(self):
        """
        If the PARTNERS_SESSION_KEY is list of valid pks of Partners, the view
        should return OK.
        """
        p1 = PartnerFactory()

        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.editor

        # Make sure there's a session key - otherwise we'll get redirected to
        # /applications/request before we hit the login test
        request.session = {views.PARTNERS_SESSION_KEY: [p1.pk]}

        response = views.SubmitApplicationView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_form_fields_match_session_keys_one_partner(self):
        """
        The fields in the constructed form should exactly match the data
        required by the partner in question.
        """
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=False,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}

        form = view.get_form(BaseApplicationForm)

        # Check user data.
        self.assertIn("real_name", form.fields)
        self.assertIn("country_of_residence", form.fields)
        self.assertNotIn("occupation", form.fields)
        self.assertNotIn("affiliation", form.fields)

        # Check partner data: p1.
        self.assertNotIn("partner_{id}_specific_stream".format(id=p1.id), form.fields)
        self.assertNotIn("partner_{id}_specific_title".format(id=p1.id), form.fields)
        self.assertNotIn(
            "partner_{id}_agreement_with_terms_of_use".format(id=p1.id), form.fields
        )
        self.assertNotIn("partner_{id}_account_email".format(id=p1.id), form.fields)
        self.assertIn("partner_{id}_rationale".format(id=p1.id), form.fields)
        self.assertIn("partner_{id}_comments".format(id=p1.id), form.fields)

    def test_form_fields_match_session_keys_two_identical_partners(self):
        """
        The fields in the constructed form should exactly match the data
        required by the partners in question.
        """
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=False,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        # This has identical conditions to p1; a form encompassing both
        # partners should have the same set of user data fields as a form with
        # only one of them.
        p2 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=False,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        # Test just p1.
        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        form = view.get_form(BaseApplicationForm)

        # Check user data.
        self.assertIn("real_name", form.fields)
        self.assertIn("country_of_residence", form.fields)
        self.assertNotIn("occupation", form.fields)
        self.assertNotIn("affiliation", form.fields)

        # Check partner data: p1.
        self.assertNotIn("partner_{id}_specific_stream".format(id=p1.id), form.fields)
        self.assertNotIn("partner_{id}_specific_title".format(id=p1.id), form.fields)
        self.assertNotIn(
            "partner_{id}_agreement_with_terms_of_use".format(id=p1.id), form.fields
        )
        self.assertNotIn("partner_{id}_account_email".format(id=p1.id), form.fields)
        self.assertIn("partner_{id}_rationale".format(id=p1.id), form.fields)
        self.assertIn("partner_{id}_comments".format(id=p1.id), form.fields)

        # Check partner data: p2.
        self.assertNotIn("partner_{id}_specific_stream".format(id=p2.id), form.fields)
        self.assertNotIn("partner_{id}_specific_title".format(id=p2.id), form.fields)
        self.assertNotIn(
            "partner_{id}_agreement_with_terms_of_use".format(id=p2.id), form.fields
        )
        self.assertNotIn("partner_{id}_account_email".format(id=p2.id), form.fields)
        self.assertIn("partner_{id}_rationale".format(id=p2.id), form.fields)
        self.assertIn("partner_{id}_comments".format(id=p2.id), form.fields)

        # Test p1 + p3: should be the more user data than above and also extra
        # partner data fields (one per partner).

    def test_form_fields_match_session_keys_two_different_partners(self):
        """
        The fields in the constructed form should exactly match the data
        required by the partners in question.
        """
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=False,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        # This has different conditions than p1; a form encompassing both
        # partners should have a different set of user data fields than a form
        # with only one of them.
        p2 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=True,
            specific_stream=False,
            occupation=True,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        form = view.get_form(BaseApplicationForm)

        # Check user data.
        self.assertIn("real_name", form.fields)
        self.assertIn("country_of_residence", form.fields)
        self.assertIn("occupation", form.fields)
        self.assertNotIn("affiliation", form.fields)

        # Check partner data: p1.
        self.assertNotIn("partner_{id}_specific_stream".format(id=p1.id), form.fields)
        self.assertNotIn("partner_{id}_specific_title".format(id=p1.id), form.fields)
        self.assertNotIn(
            "partner_{id}_agreement_with_terms_of_use".format(id=p1.id), form.fields
        )
        self.assertNotIn("partner_{id}_account_email".format(id=p1.id), form.fields)
        self.assertIn("partner_{id}_rationale".format(id=p1.id), form.fields)
        self.assertIn("partner_{id}_comments".format(id=p1.id), form.fields)

        # Check partner data: p2.
        self.assertNotIn("partner_{id}_specific_stream".format(id=p2.id), form.fields)
        self.assertIn("partner_{id}_specific_title".format(id=p2.id), form.fields)
        self.assertNotIn(
            "partner_{id}_agreement_with_terms_of_use".format(id=p2.id), form.fields
        )
        self.assertNotIn("partner_{id}_account_email".format(id=p2.id), form.fields)
        self.assertIn("partner_{id}_rationale".format(id=p2.id), form.fields)
        self.assertIn("partner_{id}_comments".format(id=p2.id), form.fields)

    def test_form_initial_data(self):
        """
        Make sure that the form prefills with user data matching whatever we
        have on file.
        """
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=False,
            specific_stream=False,
            occupation=True,
            affiliation=True,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        user = UserFactory(username="alice")
        if hasattr(user, "editor"):
            user.editor.delete()

        EditorFactory(
            user=user,
            # Same as the factory defaults, but repeated here because explicit
            # is better than implicit - let's make it obvious that our
            # assertEquals ought to be true.
            real_name="Alice Crypto",
            occupation="Cat floofer",
            # This is different from the default, because we should make sure to
            # check an empty string.
            affiliation="",
            # This is different from the default, because we should make sure to
            # check something Unicodey.
            country_of_residence="Ümláuttøwñ",
        )

        view = self._get_isolated_view(views.SubmitApplicationView, user)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}

        initial = view.get_initial()
        self.assertEqual(initial["real_name"], "Alice Crypto")
        self.assertEqual(initial["country_of_residence"], "Ümláuttøwñ")
        self.assertEqual(initial["occupation"], "Cat floofer")
        self.assertEqual(initial["affiliation"], "")

        user.delete()

    def test_403_on_bundle_application(self):
        """
        Users shouldn't be allowed to post new applications for BUNDLE
        partners, but if they try to, throw a 403
        """
        EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(authorization_method=Partner.BUNDLE)
        url = reverse("applications:apply_single", kwargs={"pk": partner.id})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_redirection_on_success(self):
        """
        Make sure we redirect to the expected page upon posting a valid form.
        """
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=False,
            specific_title=False,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
        )

        factory = RequestFactory()

        data = {
            "real_name": "Anonymous Coward",
            "partner_{id}_rationale".format(id=p1.id): "Whimsy",
            "partner_{id}_comments".format(id=p1.id): "None whatsoever",
        }

        request = factory.post(self.url, data)
        request.user = self.editor
        request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}

        response = views.SubmitApplicationView.as_view()(request)

        expected_url = reverse(
            "users:editor_detail", kwargs={"pk": self.editor.editor.pk}
        )
        self.assertEqual(response.url, expected_url)

    def test_user_data_updates_on_success(self):
        """
        When the form post includes user data, the editor profile should update
        accordingly.
        """

        # Set up database objects.
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=True,
            specific_title=False,
            specific_stream=False,
            occupation=True,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        user = UserFactory()

        EditorFactory(
            user=user,
            # All 3 of these fields will be required by PartnerFactory.
            real_name="",
            country_of_residence="Lithuania",
            occupation="Cat floofer",
        )

        data = {
            # Should fill in existing blank field.
            "real_name": "Anonymous Coward",
            # Should update existing not-blank field.
            "country_of_residence": "Bolivia",
            # Should result in no change.
            "occupation": "Cat floofer",
            "partner_{id}_rationale".format(id=p1.id): "Whimsy",
            "partner_{id}_comments".format(id=p1.id): "None whatsoever",
        }

        factory = RequestFactory()

        request = factory.post(self.url, data)
        request.user = user
        request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}

        _ = views.SubmitApplicationView.as_view()(request)
        editor = user.editor
        editor.refresh_from_db()

        self.assertEqual(editor.real_name, "Anonymous Coward")
        self.assertEqual(editor.country_of_residence, "Bolivia")
        self.assertEqual(editor.occupation, "Cat floofer")

        user.delete()

    def test_applications_created_on_success(self):
        """
        When the form posts successfully, Partner-specific Applications should
        be created.
        """

        # Set up database objects.
        p1 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=True,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )
        p2 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=False,
            specific_stream=True,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        s1 = Stream()
        s1.partner = p2
        s1.name = "Health and Biological Sciences"
        s1.save()

        # Checking our assumptions, just in case. This means that our
        # get() queries later on should not raise MultipleObjectsReturned.
        self.assertEqual(Application.objects.filter(partner=p1).count(), 0)
        self.assertEqual(Application.objects.filter(partner=p2).count(), 0)

        factory = RequestFactory()

        data = {
            "partner_{id}_rationale".format(id=p1.id): "Whimsy",
            "partner_{id}_comments".format(id=p1.id): "None whatsoever",
            "partner_{id}_specific_title".format(id=p1.id): "Open Access for n00bs",
            "partner_{id}_rationale".format(id=p2.id): "Saving the world",
            "partner_{id}_comments".format(id=p2.id): "",
            "partner_{id}_specific_stream".format(id=p2.id): s1.pk,
        }

        request = factory.post(self.url, data)
        request.user = self.editor
        request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        _ = views.SubmitApplicationView.as_view()(request)

        # If the application has not been created, these lines will raise
        # DoesNotExist.
        app1 = Application.objects.get(partner=p1, editor=self.editor.editor)
        app2 = Application.objects.get(partner=p2, editor=self.editor.editor)

        # Make sure applications have the expected properties, based on the
        # partner requirements and submitted data.
        self.assertEqual(app1.status, Application.PENDING)
        self.assertEqual(app1.rationale, "Whimsy")
        self.assertEqual(app1.comments, "None whatsoever")
        self.assertEqual(app1.specific_title, "Open Access for n00bs")
        self.assertEqual(app1.specific_stream, None)
        self.assertEqual(app1.agreement_with_terms_of_use, False)
        self.assertEqual(app1.account_email, None)

        self.assertEqual(app2.status, Application.PENDING)
        self.assertEqual(app2.rationale, "Saving the world")
        self.assertEqual(app2.comments, "")
        self.assertEqual(app2.specific_title, "")
        self.assertEqual(app2.specific_stream, s1)
        self.assertEqual(app2.agreement_with_terms_of_use, False)
        self.assertEqual(app2.account_email, None)

    def test_get_partners(self):
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        # We need to coerce the querysets to a list for the comparison to
        # work; assertQuerysetEqual on the underlying querysets fails. I'm going
        # to guess that one of the querysets is lazy and one isn't, so we have
        # to force evaluation for equality to work?
        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}
        self.assertListEqual(
            list(view._get_partners()), list(Partner.objects.filter(pk=p1.id))
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p2.id]}
        self.assertListEqual(
            list(view._get_partners()), list(Partner.objects.filter(pk=p2.id))
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}
        self.assertListEqual(
            list(view._get_partners()),
            list(Partner.objects.filter(pk__in=[p1.id, p2.id])),
        )

    def test_get_partner_fields(self):

        p1 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=True,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=True,
            account_email=False,
        )
        p2 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=False,
            specific_stream=True,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        # Use set(), because order is unimportant.
        self.assertEqual(
            set(view._get_partner_fields(p1)),
            {"specific_title", "agreement_with_terms_of_use"},
        )

        self.assertEqual(set(view._get_partner_fields(p2)), {"specific_stream"})

    def test_get_user_fields(self):

        p1 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=True,
            specific_stream=False,
            occupation=True,
            affiliation=True,
            agreement_with_terms_of_use=True,
            account_email=False,
        )
        p2 = PartnerFactory(
            real_name=True,
            country_of_residence=False,
            specific_title=False,
            specific_stream=True,
            occupation=True,
            affiliation=False,
            agreement_with_terms_of_use=False,
            account_email=False,
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        partners = Partner.objects.filter(pk__in=[p1.pk, p2.pk])

        self.assertEqual(
            set(view._get_user_fields(partners)),
            {"real_name", "occupation", "affiliation"},
        )

    def test_deleted_field_invalid(self):
        """
        When users delete their data, their applications are blanked and
        hidden. The blanking process sets text fields to "[deleted]". To
        avoid confusion, trying to submit a form with a field containing
        *only* "[deleted]" should be invalid.
        """
        p1 = PartnerFactory(
            real_name=True,
            country_of_residence=False,
            specific_title=False,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False,
        )

        data = {
            "real_name": "Anonymous Coward",
            "partner_{id}_rationale".format(id=p1.id): "[deleted]",
            "partner_{id}_comments".format(id=p1.id): "None whatsoever",
        }

        self.editor.set_password("editor")
        self.editor.save()

        client = Client()
        session = client.session
        client.login(username=self.editor, password="editor")

        form_url = reverse("applications:apply_single", kwargs={"pk": p1.pk})

        response = client.post(form_url, data)

        self.assertFormError(
            response,
            "form",
            "partner_{id}_rationale".format(id=p1.id),
            "This field consists only of restricted text.",
        )

    def test_pop_specific_stream_options(self):
        """
        For partners having multiple streams, users should only be able
        to apply for the ones they don't have an authorization to.
        """
        # Set up request.
        factory = RequestFactory()
        request = factory.get(self.url)
        user = UserFactory()
        user.email = "foo@bar.com"
        user.save()
        user.userprofile.terms_of_use = True
        user.userprofile.save()
        editor = EditorFactory(user=user)
        request.user = user
        partner = PartnerFactory(specific_stream=True)
        stream1 = StreamFactory(partner=partner)
        stream2 = StreamFactory(partner=partner)
        ApplicationFactory(
            status=Application.SENT,
            editor=editor,
            partner=partner,
            specific_stream=stream1,
        )

        request.session = {views.PARTNERS_SESSION_KEY: [partner.pk]}
        response = views.SubmitApplicationView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        option1 = '<option value="{stream_id}">{stream_name}</option>'.format(
            stream_id=stream1.id, stream_name=stream1.name
        )
        option2 = '<option value="{stream_id}">{stream_name}</option>'.format(
            stream_id=stream2.id, stream_name=stream2.name
        )
        self.assertContains(response, option2)
        # User already has an authorization for stream1 i.e. the
        # option should not be on the apply page
        self.assertNotContains(response, option1)


class ListApplicationsTest(BaseApplicationViewTest):
    @classmethod
    def setUpClass(cls):
        super(ListApplicationsTest, cls).setUpClass()
        cls.superuser = User.objects.create_user(username="super", password="super")
        cls.superuser.is_superuser = True
        cls.superuser.save()

        ApplicationFactory(status=Application.PENDING)
        ApplicationFactory(status=Application.PENDING)
        ApplicationFactory(status=Application.QUESTION)
        parent = ApplicationFactory(status=Application.APPROVED)
        ApplicationFactory(status=Application.APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.INVALID)
        ApplicationFactory(status=Application.INVALID)

        # Make sure there are some up-for-renewal querysets, too.
        ApplicationFactory(status=Application.PENDING, parent=parent)
        ApplicationFactory(status=Application.QUESTION, parent=parent)
        ApplicationFactory(status=Application.APPROVED, parent=parent)
        ApplicationFactory(status=Application.NOT_APPROVED, parent=parent)
        ApplicationFactory(status=Application.SENT, parent=parent)

        user = UserFactory(username="editor")
        editor = EditorFactory(user=user)

        # And some applications from a user who will delete their account.
        ApplicationFactory(status=Application.PENDING, editor=editor)
        ApplicationFactory(status=Application.QUESTION, editor=editor)
        ApplicationFactory(status=Application.APPROVED, editor=editor)
        ApplicationFactory(status=Application.NOT_APPROVED, editor=editor)
        ApplicationFactory(status=Application.SENT, editor=editor)

        delete_url = reverse("users:delete_data", kwargs={"pk": user.pk})

        # Need a password so we can login
        user.set_password("editor")
        user.save()

        client = Client()
        session = client.session
        client.login(username=user.username, password="editor")

        submit = client.post(delete_url)

    @classmethod
    def tearDownClass(cls):
        super(ListApplicationsTest, cls).tearDownClass()
        cls.superuser.delete()
        for app in Application.objects.all():
            app.delete()

    def _base_test_authorization(self, url, view):
        """
        Only Coordinators and superusers should be able to see application
        lists.
        """
        # An anonymous user is prompted to login.
        factory = RequestFactory()

        request = factory.get(url)
        request.user = AnonymousUser()

        # Make sure there's a session key - otherwise we'll get redirected to
        # /applications/request before we hit the login test
        p1 = PartnerFactory()
        p1.coordinator = self.coordinator
        request.session = {views.PARTNERS_SESSION_KEY: [p1.pk]}

        with self.assertRaises(PermissionDenied):
            _ = view.as_view()(request)

        # An editor who is not a coordinator may not see the page.
        request.user = self.editor
        with self.assertRaises(PermissionDenied):
            _ = view.as_view()(request)

        # A coordinator may see the page.
        request.user = self.coordinator
        response = view.as_view()(request)

        self.assertEqual(response.status_code, 200)

        # A superuser may see the page.
        superuser = UserFactory()
        superuser.is_superuser = True
        superuser.save()

        request.user = superuser
        response = view.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def _base_test_object_visibility(self, url, view, queryset):
        factory = RequestFactory()

        request = factory.get(url)
        request.user = self.coordinator

        # reponse for view when user isn't the designated coordinator
        denyResponse = view.as_view()(request)

        # We made some apps that shouldn't ever show up, which are
        # tested later, not here.
        queryset_exclude_deleted = queryset.exclude(editor=None)

        # Designate the coordinator
        for obj in queryset_exclude_deleted:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        # reponse for view when user is the designated coordinator
        allowResponse = view.as_view()(request)

        for obj in queryset_exclude_deleted:
            # Unlike Client(), RequestFactory() doesn't render the response;
            # we'll have to do that before we can check for its content.

            # Applications should not be visible to just any coordinator
            self.assertNotIn(
                escape(obj.__str__()), denyResponse.render().content.decode("utf-8")
            )

            # Applications should be visible to the designated coordinator
            self.assertIn(
                escape(obj.__str__()), allowResponse.render().content.decode("utf-8")
            )

    def test_list_authorization(self):
        url = reverse("applications:list")
        self._base_test_authorization(url, views.ListApplicationsView)

    def test_list_object_visibility(self):
        url = reverse("applications:list")
        queryset = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION]
        )
        self._base_test_object_visibility(url, views.ListApplicationsView, queryset)

    def test_list_approved_authorization(self):
        url = reverse("applications:list_approved")
        self._base_test_authorization(url, views.ListApprovedApplicationsView)

    def test_list_approved_object_visibility(self):
        url = reverse("applications:list_approved")
        queryset = Application.objects.filter(status=Application.APPROVED)
        self._base_test_object_visibility(
            url, views.ListApprovedApplicationsView, queryset
        )

    def test_list_rejected_authorization(self):
        url = reverse("applications:list_rejected")
        self._base_test_authorization(url, views.ListRejectedApplicationsView)

    def test_list_rejected_object_visibility(self):
        url = reverse("applications:list_rejected")
        queryset = Application.objects.filter(
            status__in=[Application.NOT_APPROVED, Application.INVALID]
        )
        self._base_test_object_visibility(
            url, views.ListRejectedApplicationsView, queryset
        )

    def _base_test_deleted_object_visibility(self, url, view, queryset):
        factory = RequestFactory()

        request = factory.get(url)
        request.user = self.coordinator

        # Only testing the apps from deleted users
        queryset_deleted = queryset.filter(editor=None)

        # Designate the coordinator
        for obj in queryset_deleted:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        response = view.as_view()(request)

        for obj in queryset_deleted:
            # Deleted applications should not be visible to anyone, even the
            # assigned coordinator.
            self.assertNotIn(
                escape(obj.__str__()), response.render().content.decode("utf-8")
            )

    def test_list_object_visibility(self):
        url = reverse("applications:list")
        queryset = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION]
        )
        self._base_test_deleted_object_visibility(
            url, views.ListApplicationsView, queryset
        )

    def test_list_approved_object_visibility(self):
        url = reverse("applications:list_approved")
        queryset = Application.objects.filter(status=Application.APPROVED)
        self._base_test_deleted_object_visibility(
            url, views.ListApprovedApplicationsView, queryset
        )

    def test_list_rejected_object_visibility(self):
        url = reverse("applications:list_rejected")
        queryset = Application.objects.filter(
            status__in=[Application.NOT_APPROVED, Application.INVALID]
        )
        self._base_test_deleted_object_visibility(
            url, views.ListRejectedApplicationsView, queryset
        )

    def test_list_renewal_queryset(self):
        url = reverse("applications:list_renewal")

        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.coordinator

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION], parent__isnull=False
        )

        # reponse for view when user isn't the designated coordinator
        response = views.ListRenewalApplicationsView.as_view()(request)
        deny_qs = response.context_data["object_list"]

        # Designate the coordinator
        for obj in expected_qs:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        # reponse for view when user is the designated coordinator
        response = views.ListRenewalApplicationsView.as_view()(request)
        allow_qs = response.context_data["object_list"]

        # Applications should not be visible to just any coordinator
        self.assertFalse(deny_qs)

        # Applications should be visible to the designated coordinator
        # See comment on test_queryset_unfiltered about this data structure.
        self.assertEqual(
            sorted([item.pk for item in expected_qs]),
            sorted([item.pk for item in allow_qs]),
        )

    def test_queryset_unfiltered(self):
        """
        Make sure that ListApplicationsView has the correct queryset in context
        when no filters are applied.
        """
        url = reverse("applications:list")

        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.coordinator

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION]
        ).exclude(editor=None)

        # reponse for view when user isn't the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        deny_qs = response.context_data["object_list"]

        # Designate the coordinator
        for obj in expected_qs:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        # reponse for view when user is the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        allow_qs = response.context_data["object_list"]

        # Applications should not be visible to just any coordinator
        self.assertFalse(deny_qs)

        # Applications should be visible to the designated coordinator
        # We can't use assertQuerysetEqual, because the one returned by the view
        # is ordered and this one is not. (Testing order is not important here.)
        # And simply using sorted() (or sorted(list())) on the querysets is
        # mysteriously unreliable. So we'll grab the pks of each queryset,
        # sort them, and compare *those*. This is equivalent, semantically, to
        # what we actually want ('are the same items in both querysets').
        self.assertEqual(
            sorted([item.pk for item in expected_qs]),
            sorted([item.pk for item in allow_qs]),
        )

    def _test_queryset_filtered_base(self):
        """
        Contains shared functionality for cases that make sure that
        ListApplicationsView has the correct queryset in context when filters
        are applied.
        """
        # Ensure that filtered and unfiltered Application querysets will be
        # different.
        new_editor = EditorFactory()
        ApplicationFactory(status=Application.PENDING, editor=new_editor)

        new_partner = PartnerFactory()
        ApplicationFactory(status=Application.PENDING, partner=new_partner)

        ApplicationFactory(
            status=Application.PENDING, partner=new_partner, editor=new_editor
        )

        url = reverse("applications:list")
        self.client.login(username="coordinator", password="coordinator")

        return new_editor, new_partner, url

    def test_queryset_filtered_case_1(self):
        """
        List is filtered by an editor.
        """
        new_editor, _, url = self._test_queryset_filtered_base()

        factory = RequestFactory()
        request = factory.post(url, {"editor": new_editor.pk})
        request.user = self.coordinator

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION], editor=new_editor
        )

        # reponse for view when user isn't the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        deny_qs = response.context_data["object_list"]

        # Designate the coordinator
        for obj in expected_qs:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        # reponse for view when user is the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        allow_qs = response.context_data["object_list"]

        # Applications should not be visible to just any coordinator
        self.assertFalse(deny_qs)

        # Applications should be visible to the designated coordinator
        self.assertEqual(
            sorted([item.pk for item in expected_qs]),
            sorted([item.pk for item in allow_qs]),
        )

    def test_queryset_filtered_case_2(self):
        """
        List is filtered by a partner.
        """
        _, new_partner, url = self._test_queryset_filtered_base()

        factory = RequestFactory()
        request = factory.post(url, {"partner": new_partner.pk})
        request.user = self.coordinator

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION], partner=new_partner
        )

        # reponse for view when user isn't the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        deny_qs = response.context_data["object_list"]

        # Designate the coordinator
        for obj in expected_qs:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        # reponse for view when user is the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        allow_qs = response.context_data["object_list"]

        # Applications should not be visible to just any coordinator
        self.assertFalse(deny_qs)

        # Applications should be visible to the designated coordinator
        self.assertEqual(
            sorted([item.pk for item in expected_qs]),
            sorted([item.pk for item in allow_qs]),
        )

    def test_queryset_filtered_case_3(self):
        """
        List is filtered by both editor and partner.
        """
        new_editor, new_partner, url = self._test_queryset_filtered_base()

        factory = RequestFactory()
        request = factory.post(
            url, {"editor": new_editor.pk, "partner": new_partner.pk}
        )
        request.user = self.coordinator

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION],
            editor=new_editor,
            partner=new_partner,
        )

        # reponse for view when user isn't the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        deny_qs = response.context_data["object_list"]

        # Designate the coordinator
        for obj in expected_qs:
            partner = Partner.objects.get(pk=obj.partner.pk)
            partner.coordinator = self.coordinator
            partner.save()

        # reponse for view when user is the designated coordinator
        response = views.ListApplicationsView.as_view()(request)
        allow_qs = response.context_data["object_list"]

        # Applications should not be visible to just any coordinator
        self.assertFalse(deny_qs)

        # Applications should be visible to the designated coordinator
        self.assertEqual(
            sorted([item.pk for item in expected_qs]),
            sorted([item.pk for item in allow_qs]),
        )

    def test_invalid_editor_post_handling(self):
        _, _, url = self._test_queryset_filtered_base()

        # Check assumption.
        self.assertFalse(Editor.objects.filter(pk=500))
        request = RequestFactory().post(url, data={"editor": 500})
        request.user = self.coordinator

        with self.assertRaises(Editor.DoesNotExist):
            _ = views.ListApplicationsView.as_view()(request)

    def test_invalid_partner_post_handling(self):
        _, _, url = self._test_queryset_filtered_base()

        # Check assumption.
        self.assertFalse(Partner.objects.filter(pk=500))
        request = RequestFactory().post(url, data={"partner": 500})
        request.user = self.coordinator

        with self.assertRaises(Partner.DoesNotExist):
            _ = views.ListApplicationsView.as_view()(request)

    def test_ensure_object_list_exists_case_1(self):
        """
        Case 1 is ListApplicationsView / post.

        If self.object_list does not exist, server errors can result. Since
        we override the self.object_list setting behavior on our application
        list views, we should check to ensure we haven't omitted
        self.object_list.

        We set it in get_context_data, hence the call to that. The Django
        generic view ensures this function will be called.
        """
        url = reverse("applications:list")
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {"partner": new_partner.pk})
        request.user = self.coordinator

        instance = views.ListApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_2(self):
        """
        Case 2 is ListApplicationsView / get.
        """
        url = reverse("applications:list")
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_3(self):
        """
        Case 3 is ListApprovedApplicationsView / post.
        """
        url = reverse("applications:list_approved")
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {"partner": new_partner.pk})
        request.user = self.coordinator

        instance = views.ListApprovedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_4(self):
        """
        Case 4 is ListApprovedApplicationsView / get.
        """
        url = reverse("applications:list_rejected")
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListApprovedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_5(self):
        """
        Case 5 is ListRejectedApplicationsView / post.
        """
        url = reverse("applications:list_rejected")
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {"partner": new_partner.pk})
        request.user = self.coordinator

        instance = views.ListRejectedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_6(self):
        """
        Case 4 is ListRejectedApplicationsView / get.
        """
        url = reverse("applications:list_rejected")
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListRejectedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_7(self):
        """
        Case 7 is ListRenewalApplicationsView / post.
        """
        url = reverse("applications:list_renewal")
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {"partner": new_partner.pk})
        request.user = self.coordinator

        instance = views.ListRenewalApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_8(self):
        """
        Case 8 is ListRenewalApplicationsView / get.
        """
        url = reverse("applications:list_renewal")
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListRenewalApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_9(self):
        """
        Case 9 is ListSentApplicationsView / post.
        """
        url = reverse("applications:list_renewal")
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {"partner": new_partner.pk})
        request.user = self.coordinator

        instance = views.ListSentApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def test_ensure_object_list_exists_case_10(self):
        """
        Case 10 is ListSentApplicationsView / get.
        """
        url = reverse("applications:list_renewal")
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListSentApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, "object_list"))

    def _set_up_a_bundle_and_not_a_bundle_partner(self, user):
        bundle_partner = PartnerFactory(
            authorization_method=Partner.BUNDLE, coordinator=user
        )
        not_a_bundle_partner = PartnerFactory(
            authorization_method=Partner.EMAIL, coordinator=user
        )
        return bundle_partner, not_a_bundle_partner

    def test_no_bundle_partners_in_list_view(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)
        bundle_partner, not_a_bundle_partner = self._set_up_a_bundle_and_not_a_bundle_partner(
            editor.user
        )
        bundle_app = ApplicationFactory(
            status=Application.PENDING, partner=bundle_partner, editor=editor
        )
        bundle_app_url = reverse("applications:evaluate", kwargs={"pk": bundle_app.pk})
        not_a_bundle_app = ApplicationFactory(
            status=Application.PENDING, partner=not_a_bundle_partner, editor=editor
        )
        not_a_bundle_app_url = reverse(
            "applications:evaluate", kwargs={"pk": not_a_bundle_app.pk}
        )
        response = self.client.get(reverse("applications:list"))
        self.assertNotContains(response, bundle_app_url)
        self.assertContains(response, not_a_bundle_app_url)

    def test_no_bundle_partners_in_approved_list_view(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)
        bundle_partner, not_a_bundle_partner = self._set_up_a_bundle_and_not_a_bundle_partner(
            editor.user
        )
        bundle_app = ApplicationFactory(
            status=Application.APPROVED, partner=bundle_partner, editor=editor
        )
        bundle_app_url = reverse("applications:evaluate", kwargs={"pk": bundle_app.pk})
        not_a_bundle_app = ApplicationFactory(
            status=Application.APPROVED, partner=not_a_bundle_partner, editor=editor
        )
        not_a_bundle_app_url = reverse(
            "applications:evaluate", kwargs={"pk": not_a_bundle_app.pk}
        )
        response = self.client.get(reverse("applications:list_approved"))
        self.assertNotContains(response, bundle_app_url)
        self.assertContains(response, not_a_bundle_app_url)

    def test_no_bundle_partners_in_rejected_list_view(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)
        bundle_partner, not_a_bundle_partner = self._set_up_a_bundle_and_not_a_bundle_partner(
            editor.user
        )
        bundle_app = ApplicationFactory(
            status=Application.NOT_APPROVED, partner=bundle_partner, editor=editor
        )
        bundle_app_url = reverse("applications:evaluate", kwargs={"pk": bundle_app.pk})
        not_a_bundle_app = ApplicationFactory(
            status=Application.NOT_APPROVED, partner=not_a_bundle_partner, editor=editor
        )
        not_a_bundle_app_url = reverse(
            "applications:evaluate", kwargs={"pk": not_a_bundle_app.pk}
        )
        response = self.client.get(reverse("applications:list_rejected"))
        self.assertNotContains(response, bundle_app_url)
        self.assertContains(response, not_a_bundle_app_url)

    def test_no_bundle_partners_in_renewal_list_view(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)
        bundle_partner, not_a_bundle_partner = self._set_up_a_bundle_and_not_a_bundle_partner(
            editor.user
        )
        app1 = ApplicationFactory(
            status=Application.SENT, partner=bundle_partner, editor=editor
        )
        app2 = ApplicationFactory(
            status=Application.SENT, partner=not_a_bundle_partner, editor=editor
        )
        bundle_app = ApplicationFactory(
            status=Application.PENDING,
            partner=bundle_partner,
            editor=editor,
            parent=app1,
        )
        bundle_app_url = reverse("applications:evaluate", kwargs={"pk": bundle_app.pk})
        not_a_bundle_app = ApplicationFactory(
            status=Application.PENDING,
            partner=not_a_bundle_partner,
            editor=editor,
            parent=app2,
        )
        not_a_bundle_app_url = reverse(
            "applications:evaluate", kwargs={"pk": not_a_bundle_app.pk}
        )
        response = self.client.get(reverse("applications:list_renewal"))
        self.assertNotContains(response, bundle_app_url)
        self.assertContains(response, not_a_bundle_app_url)

    def test_no_bundle_partners_in_sent_list_view(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)
        bundle_partner, not_a_bundle_partner = self._set_up_a_bundle_and_not_a_bundle_partner(
            editor.user
        )
        bundle_app = ApplicationFactory(
            status=Application.SENT, partner=bundle_partner, editor=editor
        )
        bundle_app_url = reverse("applications:evaluate", kwargs={"pk": bundle_app.pk})
        not_a_bundle_app = ApplicationFactory(
            status=Application.SENT, partner=not_a_bundle_partner, editor=editor
        )
        not_a_bundle_app_url = reverse(
            "applications:evaluate", kwargs={"pk": not_a_bundle_app.pk}
        )
        response = self.client.get(reverse("applications:list_sent"))
        self.assertNotContains(response, bundle_app_url)
        self.assertContains(response, not_a_bundle_app_url)

    def test_no_bundle_partners_in_filter_form(self):
        editor = EditorFactory()
        self.client.login(username="coordinator", password="coordinator")
        bundle_partner, not_a_bundle_partner = self._set_up_a_bundle_and_not_a_bundle_partner(
            self.coordinator
        )
        ApplicationFactory(
            status=Application.PENDING, partner=bundle_partner, editor=editor
        )
        ApplicationFactory(
            status=Application.PENDING, partner=not_a_bundle_partner, editor=editor
        )
        url = reverse("applications:list")
        factory = RequestFactory()
        # Post to filter Bundle apps only
        request = factory.post(url, {"partner": bundle_partner.pk})
        request.user = self.coordinator

        # We don't expect to see any Bundle apps
        expected_qs = Application.objects.none()
        response = views.ListApplicationsView.as_view()(request)
        allow_qs = response.context_data["object_list"]

        self.assertEqual(
            sorted([item.pk for item in expected_qs]),
            sorted([item.pk for item in allow_qs]),
        )


class RenewApplicationTest(BaseApplicationViewTest):
    def test_protected_to_self_only(self):
        partner = PartnerFactory(renewals_available=True)
        app = ApplicationFactory(
            partner=partner, status=Application.APPROVED, editor=self.editor.editor
        )

        request = RequestFactory().get(
            reverse("applications:renew", kwargs={"pk": app.pk})
        )
        request.user = self.editor

        response = views.RenewApplicationView.as_view()(request, pk=app.pk)

        self.assertEqual(response.status_code, 200)

        user2 = UserFactory()
        request.user = user2

        with self.assertRaises(PermissionDenied):
            _ = views.RenewApplicationView.as_view()(request, pk=app.pk)

    def test_getting_url_does_not_renew_app(self):
        partner = PartnerFactory(renewals_available=True)
        app = ApplicationFactory(
            partner=partner, status=Application.APPROVED, editor=self.editor.editor
        )

        self.assertTrue(app.is_renewable)  # check assumption

        request = RequestFactory().get(
            reverse("applications:renew", kwargs={"pk": app.pk})
        )
        request.user = self.editor

        _ = views.RenewApplicationView.as_view()(request, pk=app.pk)

        app.refresh_from_db()
        self.assertTrue(app.is_renewable)
        self.assertFalse(Application.objects.filter(parent=app))

    def test_restricted_renewal(self):
        # Users with restricted processing shouldn't be able to renew
        # an application.
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False, Restricted=True)
        partner = PartnerFactory(
            renewals_available=True,
            authorization_method=Partner.EMAIL,
            account_email=False,
            requested_access_duration=False,
        )
        app = ApplicationFactory(
            partner=partner, status=Application.APPROVED, editor=editor
        )

        renewal_url = reverse("applications:renew", kwargs={"pk": app.pk})

        response = self.client.get(renewal_url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_renewal_with_no_field_required(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(
            renewals_available=True,
            authorization_method=Partner.EMAIL,
            account_email=False,
            requested_access_duration=False,
        )
        app = ApplicationFactory(
            partner=partner, status=Application.APPROVED, editor=editor
        )

        renewal_url = reverse("applications:renew", kwargs={"pk": app.pk})
        response = self.client.get(renewal_url, follow=True)
        renewal_form = response.context["form"]

        self.assertTrue(renewal_form["return_url"])
        self.assertEqual(renewal_form["return_url"].value(), "/users/")

        self.client.post(
            renewal_url, {"return_url": renewal_form["return_url"].value()}
        )
        app.refresh_from_db()
        self.assertFalse(app.is_renewable)
        self.assertTrue(Application.objects.filter(parent=app))

    def test_renewal_with_different_fields_required(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(
            renewals_available=True,
            authorization_method=Partner.EMAIL,
            account_email=True,  # require account_email on renewal
            requested_access_duration=False,
        )
        app = ApplicationFactory(
            partner=partner, status=Application.APPROVED, editor=editor
        )

        renewal_url = reverse("applications:renew", kwargs={"pk": app.pk})
        response = self.client.get(renewal_url, follow=True)
        renewal_form = response.context["form"]
        self.assertTrue(renewal_form["account_email"])

        data = renewal_form.initial
        data["account_email"] = "test@example.com"
        data["return_url"] = renewal_form["return_url"].value()

        self.client.post(renewal_url, data)
        app.refresh_from_db()
        self.assertFalse(app.is_renewable)
        self.assertTrue(Application.objects.filter(parent=app))

        partner.authorization_method = Partner.PROXY
        partner.requested_access_duration = True  # require duration of access
        partner.save()

        editor1 = EditorCraftRoom(self, Terms=True, Coordinator=False)
        app1 = ApplicationFactory(
            partner=partner,
            status=Application.SENT,  # proxy applications are directly marked SENT
            editor=editor1,
        )

        renewal_url = reverse("applications:renew", kwargs={"pk": app1.pk})
        response = self.client.get(renewal_url, follow=True)
        renewal_form = response.context["form"]
        self.assertTrue(renewal_form["account_email"])
        self.assertTrue(renewal_form["requested_access_duration"])

        data = renewal_form.initial
        data["account_email"] = "test@example.com"
        data["return_url"] = renewal_form["return_url"].value()
        data["requested_access_duration"] = 6

        self.client.post(renewal_url, data)
        app1.refresh_from_db()
        self.assertFalse(app1.is_renewable)
        app2 = Application.objects.filter(parent=app1)
        app2 = app2.first()
        # Make sure everything is in place in the app
        self.assertEqual(app2.account_email, "test@example.com")
        self.assertEqual(app2.requested_access_duration, 6)

    def test_renewal_extends_access_duration(self):
        # Tests that an approved renewal sets the correct, extended, expiry date
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(
            renewals_available=True,
            authorization_method=Partner.PROXY,
            account_email=True,  # require account_email on renewal
            requested_access_duration=True,
        )
        app = ApplicationFactory(
            partner=partner,
            status=Application.APPROVED,
            editor=editor,
            requested_access_duration=3,
        )

        renewal_url = reverse("applications:renew", kwargs={"pk": app.pk})
        response = self.client.get(renewal_url, follow=True)
        renewal_form = response.context["form"]

        data = renewal_form.initial
        data["account_email"] = "test@example.com"
        data["return_url"] = renewal_form["return_url"].value()
        data["requested_access_duration"] = 6

        self.client.post(renewal_url, data)
        app.refresh_from_db()

        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        partner.coordinator = coordinator.user
        partner.save()

        renewal_app = Application.objects.get(parent=app)
        # Approve the renewal request
        app_url = reverse("applications:evaluate", kwargs={"pk": renewal_app.pk})
        # Approve the application
        response = self.client.post(
            app_url, data={"status": Application.APPROVED}, follow=True
        )

        renewal_app.refresh_from_db()
        auth = renewal_app.get_authorization()
        six_months_from_now = date.today() + relativedelta(months=+6)
        self.assertEqual(auth.date_expires, six_months_from_now)

    def test_bundle_app_renewal_raises_permission_denied(self):
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)
        partner = PartnerFactory(authorization_method=Partner.BUNDLE)
        app = ApplicationFactory(
            status=Application.SENT, partner=partner, editor=editor
        )
        request = RequestFactory().get(
            reverse("applications:renew", kwargs={"pk": app.pk})
        )
        request.user = editor.user
        with self.assertRaises(PermissionDenied):
            views.RenewApplicationView.as_view()(request, pk=app.pk)


class ApplicationModelTest(TestCase):
    def test_approval_sets_date_closed(self):
        app = ApplicationFactory(status=Application.PENDING, date_closed=None)
        self.assertFalse(app.date_closed)

        app.status = Application.APPROVED
        app.save()

        self.assertTrue(app.date_closed)
        self.assertEqual(app.date_closed, date.today())

    def test_approval_sets_days_open(self):
        app = ApplicationFactory(status=Application.PENDING, date_closed=None)
        self.assertEqual(app.days_open, None)

        app.status = Application.APPROVED
        app.save()

        self.assertEqual(app.days_open, 0)

    def test_rejection_sets_date_closed(self):
        app = ApplicationFactory(status=Application.PENDING, date_closed=None)
        self.assertFalse(app.date_closed)

        app.status = Application.NOT_APPROVED
        app.save()

        self.assertTrue(app.date_closed)
        self.assertEqual(app.date_closed, date.today())

    def test_rejection_sets_days_open(self):
        # date_created will be auto set to today
        app = ApplicationFactory(status=Application.PENDING, date_closed=None)
        self.assertTrue(app.days_open == None)

        app.status = Application.NOT_APPROVED
        app.save()

        self.assertTrue(app.days_open == 0)

    def test_bootstrap_class(self):
        app = ApplicationFactory(status=Application.PENDING)
        self.assertEqual(app.get_bootstrap_class(), "-primary")

        app.status = Application.QUESTION
        app.save()
        self.assertEqual(app.get_bootstrap_class(), "-warning")

        app.status = Application.APPROVED
        app.save()
        self.assertEqual(app.get_bootstrap_class(), "-success")

        app.status = Application.NOT_APPROVED
        app.save()
        self.assertEqual(app.get_bootstrap_class(), "-danger")

    def test_get_version_count(self):
        app = ApplicationFactory()

        # On creation apps have only one version.
        self.assertEqual(app.get_version_count(), 1)

        # Make a change to the app and save it - now there should be one
        # version.
        app.status = Application.QUESTION
        app.save()
        self.assertEqual(app.get_version_count(), 2)

        # What the heck.
        app.status = Application.APPROVED
        app.save()
        self.assertEqual(app.get_version_count(), 3)

        # We're just gonna have to hope this continues inductively.

    def test_get_latest_version(self):
        app = ApplicationFactory(
            status=Application.PENDING, rationale="for great justice"
        )

        orig_version = app.get_latest_version()
        self.assertTrue(isinstance(orig_version, reversion.models.Version))

        self.assertEqual(orig_version.field_dict["status"], Application.PENDING)
        self.assertEqual(orig_version.field_dict["rationale"], "for great justice")

        app.status = Application.QUESTION
        app.save()

        new_version = app.get_latest_version()
        self.assertTrue(isinstance(new_version, reversion.models.Version))
        self.assertEqual(new_version.field_dict["status"], Application.QUESTION)
        self.assertEqual(new_version.field_dict["rationale"], "for great justice")

    def test_get_latest_revision(self):
        app = ApplicationFactory()

        orig_revision = app.get_latest_revision()
        self.assertTrue(isinstance(orig_revision, reversion.models.Revision))

        app.status = Application.QUESTION
        app.save()

        new_revision = app.get_latest_revision()
        self.assertTrue(isinstance(new_revision, reversion.models.Revision))
        self.assertNotEqual(orig_revision, new_revision)

    def test_is_renewable(self):
        # Applications which are a parent cannot be renewed, even if other
        # criteria are OK.
        partner = PartnerFactory(renewals_available=True)
        app1 = ApplicationFactory(status=Application.APPROVED, partner=partner)
        app2 = ApplicationFactory()
        app2.parent = app1
        app2.save()

        self.assertFalse(app1.is_renewable)

        # Applications whose status is not APPROVED or SENT cannot be renewed,
        # even if other criteria are OK.
        app_pending = ApplicationFactory(status=Application.PENDING, partner=partner)
        self.assertFalse(app_pending.is_renewable)

        app_question = ApplicationFactory(status=Application.QUESTION, partner=partner)
        self.assertFalse(app_question.is_renewable)

        app_not_approved = ApplicationFactory(
            status=Application.NOT_APPROVED, partner=partner
        )
        self.assertFalse(app_not_approved.is_renewable)

        # Applications whose partners don't have renewals_available cannot be
        # renewed.
        partner2 = PartnerFactory(renewals_available=False)
        app = ApplicationFactory(partner=partner2, status=Application.APPROVED)
        self.assertFalse(app.is_renewable)

        # Other applications can be renewed!
        good_app = ApplicationFactory(partner=partner, status=Application.APPROVED)
        self.assertTrue(good_app.is_renewable)

        good_app2 = ApplicationFactory(partner=partner, status=Application.SENT)
        self.assertTrue(good_app.is_renewable)

        delete_me = [
            app1,
            app2,
            app_pending,
            app_question,
            app_not_approved,
            app,
            good_app,
            good_app2,
        ]

        for app in delete_me:
            app.delete()

    def test_renew_good_app(self):
        stream = StreamFactory()
        editor = EditorFactory()
        editor2 = EditorFactory()
        partner = PartnerFactory(renewals_available=True)
        app = ApplicationFactory(
            rationale="Because I said so",
            specific_title="The one with the blue cover",
            specific_stream=stream,
            comments="No comment",
            agreement_with_terms_of_use=True,
            account_email="bob@example.com",
            editor=editor,
            partner=partner,
            status=Application.APPROVED,
            date_closed=date.today() + timedelta(days=1),
            days_open=1,
            sent_by=editor2.user,
        )

        app2 = app.renew()

        # Just checking.
        self.assertTrue(isinstance(app2, Application))

        # Fields that should be copied, were.
        self.assertEqual(app2.rationale, "Because I said so")
        self.assertEqual(app2.specific_title, "The one with the blue cover")
        self.assertEqual(app2.specific_stream, stream)
        self.assertEqual(app2.comments, "No comment")
        self.assertEqual(app2.agreement_with_terms_of_use, True)
        self.assertEqual(app2.account_email, "bob@example.com")
        self.assertEqual(app2.editor, editor)
        self.assertEqual(app2.partner, partner)

        # Fields that should be cleared or reset, were.
        self.assertEqual(app2.status, Application.PENDING)
        self.assertFalse(app2.date_closed)
        self.assertFalse(app2.days_open)
        self.assertFalse(app2.sent_by)
        self.assertEqual(app2.parent, app)

    def test_renew_bad_app(self):
        partner = PartnerFactory(renewals_available=False)
        app = ApplicationFactory(partner=partner)
        self.assertFalse(app.renew())

    def test_deleted_user_app_blanked(self):
        """
        Test that applications from users who have deleted their data
        have their data wiped correctly.
        """
        user = UserFactory(username="editor")
        editor = EditorFactory(user=user)
        partner = PartnerFactory()
        app = ApplicationFactory(
            rationale="Because I said so",
            comments="No comment",
            agreement_with_terms_of_use=True,
            account_email="bob@example.com",
            editor=editor,
            partner=partner,
            status=Application.APPROVED,
            date_closed=date.today() + timedelta(days=1),
            days_open=1,
            sent_by=user,
        )

        delete_url = reverse("users:delete_data", kwargs={"pk": user.pk})

        # Need a password so we can login
        user.set_password("editor")
        user.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=user.username, password="editor")

        submit = self.client.post(delete_url)
        app.refresh_from_db()

        assert (
            app.editor == None
            and app.rationale == "[deleted]"
            and app.account_email == "[deleted]"
            and app.comments == "[deleted]"
        )

    def test_coordinator_delete(self):
        """
        We came across a bug where editors were being removed from
        applications where the sent_by user deleted their data.
        This test verifies that's not still happening.
        """
        user = UserFactory()
        editor = EditorFactory(user=user)
        coordinator = UserFactory()
        coordinator_editor = EditorFactory(user=coordinator)
        get_coordinators().user_set.add(coordinator)

        application = ApplicationFactory(editor=editor, sent_by=coordinator)

        # Need a password so we can login
        coordinator.set_password("editor")
        coordinator.save()

        client = Client()
        session = client.session
        client.login(username=coordinator.username, password="editor")

        delete_url = reverse("users:delete_data", kwargs={"pk": coordinator.pk})
        submit = client.post(delete_url)

        application.refresh_from_db()
        assert application.editor == editor

    def test_stream_delete(self):
        # Null out specific_stream for application if the stream gets deleted.
        # This is important for appropriately handling partner/stream configuration changes.
        user = UserFactory()
        editor = EditorFactory(user=user)
        coordinator = UserFactory()
        get_coordinators().user_set.add(coordinator)
        partner = PartnerFactory(
            specific_stream=True, authorization_method=Partner.EMAIL
        )
        stream = StreamFactory(partner=partner, authorization_method=Partner.EMAIL)
        app = ApplicationFactory(
            rationale="Because I said so",
            comments="No comment",
            agreement_with_terms_of_use=True,
            account_email="bob@example.com",
            editor=editor,
            partner=partner,
            specific_stream=stream,
            status=Application.SENT,
            date_closed=date.today() + timedelta(days=1),
            days_open=1,
            sent_by=coordinator,
        )
        # This app should show up in stream specific queries.
        self.assertEqual(
            Application.objects.filter(
                pk=app.pk, specific_stream=stream.pk, editor=editor
            ).count(),
            1,
        )
        # Delete the stream.
        stream_pk = stream.pk
        stream.delete()
        # This app should no longer show up in stream specific queries.
        self.assertEqual(
            Application.objects.filter(
                pk=app.pk, specific_stream=stream_pk, editor=editor
            ).count(),
            0,
        )
        # But it should still be there.
        self.assertEqual(
            Application.objects.filter(pk=app.pk, editor=editor).count(), 1
        )

    def test_get_authorization(self):
        # Approve an application so that we create an authorization
        partner = PartnerFactory(
            authorization_method=Partner.PROXY, requested_access_duration=True
        )
        application = ApplicationFactory(partner=partner, status=Application.PENDING)
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        application.partner.coordinator = coordinator.user
        application.partner.save()

        url = reverse("applications:evaluate", kwargs={"pk": application.pk})
        response = self.client.post(
            url, data={"status": Application.APPROVED}, follow=True
        )

        # Check that we're fetching the correct authorization
        authorization = Authorization.objects.get(
            user=application.editor.user, partners=application.partner
        )
        self.assertEqual(application.get_authorization(), authorization)


class EvaluateApplicationTest(TestCase):
    def setUp(self):

        super(EvaluateApplicationTest, self).setUp()
        self.editor = EditorFactory()
        self.user = self.editor.user

        self.partner = PartnerFactory()

        self.application = ApplicationFactory(
            editor=self.editor,
            status=Application.PENDING,
            partner=self.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )
        self.url = reverse("applications:evaluate", kwargs={"pk": self.application.pk})

        editor2 = EditorFactory()
        self.user_restricted = editor2.user
        get_restricted().user_set.add(self.user_restricted)

        self.restricted_application = ApplicationFactory(
            editor=editor2,
            status=Application.PENDING,
            partner=self.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )
        self.url_restricted = reverse(
            "applications:evaluate", kwargs={"pk": self.restricted_application.pk}
        )

        self.coordinator = UserFactory(username="coordinator")
        self.coordinator.set_password("coordinator")
        coordinators = get_coordinators()
        coordinators.user_set.add(self.coordinator)
        self.coordinator.userprofile.terms_of_use = True
        self.coordinator.userprofile.save()

        self.message_patcher = patch("TWLight.applications.views.messages.add_message")
        self.message_patcher.start()

    def tearDown(self):
        super(EvaluateApplicationTest, self).tearDown()
        self.message_patcher.stop()

    def test_sets_status(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.APPROVED)

    def test_sets_status_sent_for_proxy_partner(self):
        """
        In here we test if we correctly mark approved applications
        for proxy partners as sent.
        """
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.save()

        self.partner.authorization_method = Partner.PROXY
        # Approval won't work if proxy partner is not available/waitlisted
        self.partner.status = Partner.AVAILABLE
        self.partner.save()

        self.partner.coordinator = EditorCraftRoom(
            self, Terms=True, Coordinator=True
        ).user
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # Approved applications are treated as sent for proxy partners
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.SENT)

    def test_sets_status_approved_for_proxy_partner_with_authorizations(self):
        """
        We test different behaviours of applications/partners when we approve
        applications for proxy partners by tweaking various parameters.
        """
        factory = RequestFactory()

        # Accounts are available, at least one inactive authorization, not waitlisted - approval works
        self.application.status = Application.PENDING
        self.application.save()

        self.partner.authorization_method = Partner.PROXY
        # Approval won't work if proxy partner is not available/waitlisted
        self.partner.status = Partner.AVAILABLE
        # To trigger the code that crunches the numbers to allow approvals
        self.partner.accounts_available = 10
        self.partner.save()

        self.partner.coordinator = EditorCraftRoom(
            self, Terms=True, Coordinator=True
        ).user
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # Approved applications are treated as sent for proxy partners
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.SENT)

        # Partner is waitlisted - approvals disallowed
        self.application.status = Application.PENDING
        self.application.save()

        self.partner.status = Partner.WAITLIST
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.PENDING)

        # Partner has not enough accounts available - approvals disallowed
        # Reset application status
        self.application.status = Application.PENDING
        self.application.save()

        # To trigger the code that crunches the numbers to stop approvals
        self.partner.accounts_available = 2
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.PENDING)

        self.partner.accounts_available = 3
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.PENDING)

        self.partner.refresh_from_db()
        self.assertEqual(self.partner.status, Partner.WAITLIST)

    def test_count_valid_authorizations(self):
        for _ in range(5):
            # valid
            auth1 = Authorization(
                user=EditorFactory().user,
                authorizer=self.coordinator,
                date_expires=date.today() + timedelta(days=random.randint(0, 5)),
            )
            auth1.save()
            auth1.partners.add(self.partner)
            # invalid
            auth2 = Authorization(
                user=EditorFactory().user,
                authorizer=self.coordinator,
                date_expires=date.today() - timedelta(days=random.randint(1, 5)),
            )
            auth2.save()
            auth2.partners.add(self.partner)

        # no expiry date; yet still, valid
        auth3 = Authorization(user=EditorFactory().user, authorizer=self.coordinator)
        auth3.save()
        auth3.partners.add(self.partner)

        # invalid (no authorizer)
        auth4 = Authorization(
            user=EditorFactory().user,
            date_expires=date.today() - timedelta(days=random.randint(1, 5)),
        )
        auth4.save()
        auth4.partners.add(self.partner)

        total_valid_authorizations = count_valid_authorizations(self.partner)
        self.assertEqual(total_valid_authorizations, 6)

        stream = StreamFactory(partner=self.partner)
        for _ in range(5):
            # valid
            auth5 = Authorization(
                user=EditorFactory().user,
                stream=stream,
                authorizer=self.coordinator,
                date_expires=date.today() + timedelta(days=random.randint(0, 5)),
            )
            auth5.save()
            auth5.partners.add(self.partner)
            # valid
            auth6 = Authorization(
                user=EditorFactory().user,
                stream=stream,
                authorizer=self.coordinator,
                date_expires=date.today() - timedelta(days=random.randint(1, 5)),
            )
            auth6.save()
            auth6.partners.add(self.partner)
        total_valid_authorizations = count_valid_authorizations(self.partner, stream)
        self.assertEqual(total_valid_authorizations, 5)

        # Filter logic in .helpers.get_valid_authorizations and
        # TWLight.users.models.Authorization.is_valid must be in sync.
        # We test that here.
        all_authorizations_using_is_valid = Authorization.objects.filter(
            partners=self.partner
        )
        total_valid_authorizations_using_helper = count_valid_authorizations(
            self.partner
        )

        total_valid_authorizations_using_is_valid = 0
        for each_auth in all_authorizations_using_is_valid:
            if each_auth.is_valid:
                total_valid_authorizations_using_is_valid += 1

        self.assertEqual(
            total_valid_authorizations_using_is_valid,
            total_valid_authorizations_using_helper,
        )

    def test_sets_days_open(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # Verify days open
        self.application.refresh_from_db()
        self.assertEqual(self.application.days_open, 3)

    def test_sets_date_closed(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # Verify date closed
        self.application.refresh_from_db()
        self.assertEqual(self.application.date_closed, date.today())

    def test_form_present_not_restricted(self):
        factory = RequestFactory()

        # Coordinator needs to be linked to the partner
        # so we don't get a 302
        self.partner.coordinator = self.coordinator
        self.partner.save()

        request = factory.get(self.url)
        request.user = self.coordinator

        response = views.EvaluateApplicationView.as_view()(
            request, pk=self.application.pk
        )
        self.assertIn("<form", response.render().content.decode("utf-8"))

    def test_form_not_present_restricted(self):
        factory = RequestFactory()

        # Coordinator needs to be linked to the partner
        # so we don't get a 302
        self.partner.coordinator = self.coordinator
        self.partner.save()

        request = factory.get(self.url_restricted)
        request.user = self.coordinator

        response = views.EvaluateApplicationView.as_view()(
            request, pk=self.restricted_application.pk
        )
        self.assertNotIn("<form", response.render().content.decode("utf-8"))

    def test_deleted_user_app_visibility(self):
        # If a user deletes their data, any applications
        # they had should return a 404, even for coordinators.
        delete_url = reverse("users:delete_data", kwargs={"pk": self.user.pk})

        # Need a password so we can login
        self.user.set_password("editor")
        self.user.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.user.username, password="editor")

        submit = self.client.post(delete_url)
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.coordinator

        self.partner.coordinator = self.coordinator
        self.partner.save()

        with self.assertRaises(Http404):
            _ = views.EvaluateApplicationView.as_view()(request, pk=self.application.pk)

    def _add_a_comment_and_trigger_the_signal(self, request):
        CT = ContentType.objects.get_for_model

        comm = Comment.objects.create(
            content_type=CT(Application),
            object_pk=self.application.pk,
            user=self.coordinator,
            user_name=self.coordinator.username,
            user_email=self.coordinator.email,
            comment="A comment",
            site_id=site_id(),
        )
        comm.save()

        comment_was_posted.send(sender=Comment, comment=comm, request=request)

    def test_under_discussion_signal(self):
        """
        Test comment signal fires correctly, updating Pending
        applications to Under Discussion except for Bundle partners
        """
        self.application.status = Application.PENDING
        self.application.save()

        factory = RequestFactory()
        request = factory.post(get_form_target())
        request.user = UserFactory()
        EditorFactory(user=self.coordinator)

        self._add_a_comment_and_trigger_the_signal(request)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.QUESTION)

        # Comment posted in application made to BUNDLE partner
        original_partner = self.application.partner
        self.application.partner = PartnerFactory(authorization_method=Partner.BUNDLE)
        self.application.status = Application.PENDING
        self.application.save()

        self._add_a_comment_and_trigger_the_signal(request)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.PENDING)

        self.application.partner = original_partner
        self.application.save()

    def test_immediately_sent_collection(self):
        """
        Given a collection with the Partner.LINK authorization method,
        an application flagged as APPROVED should update to SENT.
        """
        factory = RequestFactory()

        self.partner.specific_stream = True
        self.partner.save()
        stream = StreamFactory(partner=self.partner)
        stream.authorization_method = Partner.LINK
        stream.save()

        self.application.status = Application.PENDING
        self.application.specific_stream = stream
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.coordinator = coordinator.user
        self.partner.authorization_method = Partner.LINK
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # Verify status
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.SENT)

    def test_immediately_sent(self):
        """
        Given a partner with the Partner.LINK authorization method,
        an application flagged as APPROVED should update to SENT.
        """
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.coordinator = coordinator.user
        self.partner.authorization_method = Partner.LINK
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # Verify status
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.SENT)

    def test_user_instructions_email(self):
        """
        For a partner with the Partner.LINK authorization method,
        approving an application should send an email containing
        user_instructions.
        """
        factory = RequestFactory()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.authorization_method = Partner.LINK
        self.partner.user_instructions = "Instructions for account setup."
        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # We expect that one email should now be sent.
        self.assertEqual(len(mail.outbox), 1)

        # The email should contain user_instructions
        self.assertTrue(self.partner.user_instructions in mail.outbox[0].body)

    def test_user_instructions_email_collection(self):
        """
        For a collection with the Partner.LINK authorization method,
        approving an application should send an email containing
        user_instructions.
        """
        factory = RequestFactory()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.specific_stream = True
        self.partner.coordinator = coordinator.user
        self.partner.save()

        stream = StreamFactory(partner=self.partner)
        stream.authorization_method = Partner.LINK
        stream.user_instructions = "Instructions for account setup."
        stream.save()

        self.application.specific_stream = stream
        self.application.save()

        # Approve the application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        # We expect that one email should now be sent.
        self.assertEqual(len(mail.outbox), 1)

        # The email should contain user_instructions
        self.assertTrue(stream.user_instructions in mail.outbox[0].body)

    def test_sent_by_assignment(self):
        # sent_by wasn't being set when applications were marked as sent
        # from the evaluate view. This checks that's working correctly.
        factory = RequestFactory()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Send the application
        response = self.client.post(
            self.url, data={"status": Application.SENT}, follow=True
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.sent_by, coordinator.user)

    def test_notify_applicants_tou_changes(self):
        # Run the command which should add comments to outstanding apps.
        call_command("notify_applicants_tou_changes")
        # Filter apps with the same queryset as the above command.
        pending_apps = (
            Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION],
                partner__status__in=[Partner.AVAILABLE],
                editor__isnull=False,
                editor__user__userprofile__terms_of_use=False,
            )
            .exclude(editor__user__groups__name="restricted")
            .order_by("status", "partner", "date_created")
        )
        twl_comment_count = 0
        twl_team = User.objects.get(username="TWL Team")
        # Loop through the apps and count comments from twl_team.
        for app in pending_apps:
            twl_comment_count += Comment.objects.filter(
                object_pk=str(app.pk), site_id=site_id(), user=twl_team
            ).count()
        # Run the command again, which should not add more comments to outstanding apps.
        call_command("notify_applicants_tou_changes")
        # Assert that we have at least one pending app; if other tests leave no pending_apps, we want to fail here
        # because that might mask a problem with the command that causes it to leave no comments.
        self.assertGreater(pending_apps.count(), 0)
        # Assert one twl_team comment per pending_app.
        self.assertEqual(twl_comment_count, pending_apps.count())

    def test_everything_is_rendered_as_intended(self):
        EditorCraftRoom(self, Terms=False, editor=self.editor)
        response = self.client.get(self.url)
        pk = self.application.pk
        # Users visiting EvaluateApplication are redirected to ToU if they
        # agreed to it and redirected back
        terms_url = (
            reverse("terms")
            + "?next="
            + urllib.parse.quote_plus("/applications/evaluate/{}/".format(pk))
        )
        self.assertRedirects(response, terms_url)
        # Editor agrees to the terms of use
        EditorCraftRoom(self, Terms=True, editor=self.editor, Coordinator=False)
        # Visits the App Eval page
        response = self.client.get(self.url)

        # If there are less than 5 characters in the name of this
        # month, the date is written in full ("April"). If it's
        # longer, like November, it's shortened to "Nov.".
        today = date.today()
        if len(today.strftime("%B")) > 5:
            formatted_date = today.strftime("%b. %-d, %Y")
        else:
            formatted_date = today.strftime("%B %-d, %Y")
        self.assertContains(response, formatted_date)
        self.assertContains(response, self.application.status)
        self.assertContains(
            response, html.escape(self.application.partner.company_name)
        )
        self.assertContains(response, self.application.rationale)
        # Only one 'Yes' and that too for terms of use
        self.assertContains(response, "Yes")
        # Personal data should be visible only to self
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.editor.real_name)
        self.assertContains(response, self.editor.country_of_residence)
        self.assertContains(response, self.editor.occupation)
        self.assertContains(response, self.editor.affiliation)
        # Users shouldn't see some things coordinators see
        self.assertNotContains(response, "Evaluate application")
        self.assertNotContains(response, "select")  # form to change app status

        # Now let's make the coordinator visit the same page
        # In the meantime, editor has disagreed to the terms of use
        self.user.userprofile.terms_of_use = False
        self.user.userprofile.save()
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        # Not all coordinators can visit every application
        self.partner.coordinator = coordinator.user
        self.partner.save()
        response = self.client.get(self.url)
        self.assertContains(response, formatted_date)
        self.assertContains(response, self.application.status)
        self.assertContains(
            response, html.escape(self.application.partner.company_name)
        )
        self.assertContains(response, self.application.rationale)
        # No terms of use
        self.assertContains(
            response,
            # This is copied verbatim from the app eval page.
            # Change if necessary.
            "Please request the applicant "
            "agree to the site's terms of use before approving this application.",
        )
        # Personal data should *NOT* be visible to coordinators
        self.assertNotContains(response, self.user.email)
        self.assertNotContains(response, self.editor.real_name)
        self.assertNotContains(response, self.editor.country_of_residence)
        self.assertNotContains(response, self.editor.occupation)
        self.assertNotContains(response, self.editor.affiliation)
        # Coordinators can evaluate application
        self.assertContains(response, "Evaluate application")
        self.assertContains(response, "select")  # form to change app status
        # Some additional user info is visible to whoever has permissions to
        # visit this page, but it's more relevant to coordinators. So, we
        # test this page as a coordinator.
        self.assertContains(response, self.editor.wp_username)
        self.assertContains(response, self.editor.contributions)
        self.assertContains(response, self.editor.wp_editcount)

    def test_modify_app_status_from_invalid_to_anything(self):
        """
        when a coordinator tries to modify application status from
        INVALID to anything it should return the coordinator back to 
        the application with an error message.
        """
        factory = RequestFactory()

        # Marking status of the application as INVALID
        self.application.status = Application.INVALID
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Now trying to change the status of application
        response = self.client.post(
            self.url, data={"status": Application.APPROVED}, follow=True
        )

        self.application.refresh_from_db()

        # The status should remain same as INVALID
        self.assertEqual(self.application.status, Application.INVALID)

        # It should redirect to the same page
        self.assertRedirects(
            response,
            reverse("applications:evaluate", kwargs={"pk": self.application.pk}),
        )

    def test_no_status_form_for_bundle_partners(self):
        partner = PartnerFactory(authorization_method=Partner.BUNDLE)
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        partner.coordinator = coordinator.user
        partner.save()
        application = ApplicationFactory(status=Application.PENDING, partner=partner)
        url = reverse("applications:evaluate", kwargs={"pk": application.pk})
        response = self.client.get(url)
        # Applications made to Bundle partners should not have a select
        # status form
        self.assertNotContains(response, 'name="status"')
        coordinator.user.is_superuser = True
        coordinator.user.save()
        response = self.client.get(url)
        # Not even for coordinators
        self.assertNotContains(response, 'name="status"')

    class ListApplicationsTest(BaseApplicationViewTest):
        @classmethod
        def setUpClass(cls):
            super(ListApplicationsTest, cls).setUpClass()
            cls.superuser = User.objects.create_user(username="super", password="super")
            cls.superuser.is_superuser = True
            cls.superuser.save()

            ApplicationFactory(status=Application.PENDING)
            ApplicationFactory(status=Application.PENDING)
            ApplicationFactory(status=Application.QUESTION)
            parent = ApplicationFactory(status=Application.APPROVED)
            ApplicationFactory(status=Application.APPROVED)
            ApplicationFactory(status=Application.NOT_APPROVED)
            ApplicationFactory(status=Application.NOT_APPROVED)
            ApplicationFactory(status=Application.NOT_APPROVED)
            ApplicationFactory(status=Application.INVALID)
            ApplicationFactory(status=Application.INVALID)

            # Make sure there are some up-for-renewal querysets, too.
            ApplicationFactory(status=Application.PENDING, parent=parent)
            ApplicationFactory(status=Application.QUESTION, parent=parent)
            ApplicationFactory(status=Application.APPROVED, parent=parent)
            ApplicationFactory(status=Application.NOT_APPROVED, parent=parent)
            ApplicationFactory(status=Application.SENT, parent=parent)

            user = UserFactory(username="editor")
            editor = EditorFactory(user=user)

            # And some applications from a user who will delete their account.
            ApplicationFactory(status=Application.PENDING, editor=editor)
            ApplicationFactory(status=Application.QUESTION, editor=editor)
            ApplicationFactory(status=Application.APPROVED, editor=editor)
            ApplicationFactory(status=Application.NOT_APPROVED, editor=editor)
            ApplicationFactory(status=Application.SENT, editor=editor)


class SignalsUpdateApplicationsTest(BaseApplicationViewTest):
    @classmethod
    def setUpClass(cls):
        super(SignalsUpdateApplicationsTest, cls).setUpClass()

        parent = ApplicationFactory(status=Application.APPROVED)
        user = UserFactory(username="editor")
        editor = EditorFactory(user=user)

        ApplicationFactory(status=Application.PENDING)
        ApplicationFactory(status=Application.PENDING)
        ApplicationFactory(status=Application.QUESTION)
        ApplicationFactory(status=Application.APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.INVALID)
        ApplicationFactory(status=Application.INVALID)

        # Make sure there are some up-for-renewal querysets, too.
        ApplicationFactory(status=Application.PENDING, parent=parent)
        ApplicationFactory(status=Application.QUESTION, parent=parent)
        ApplicationFactory(status=Application.APPROVED, parent=parent)
        ApplicationFactory(status=Application.NOT_APPROVED, parent=parent)
        ApplicationFactory(status=Application.SENT, parent=parent)

        # And some applications from a user who will delete their account.
        ApplicationFactory(status=Application.PENDING, editor=editor)
        ApplicationFactory(status=Application.QUESTION, editor=editor)
        ApplicationFactory(status=Application.APPROVED, editor=editor)
        ApplicationFactory(status=Application.NOT_APPROVED, editor=editor)
        ApplicationFactory(status=Application.SENT, editor=editor)

    def test_invalidate_bundle_partner_applications_signal(self):
        """
        Test partner post_save signal fires correctly, updating Open applications for bundle partners to Invalid.
        """

        available_partners = Partner.objects.filter(status__in=[Partner.AVAILABLE])

        # count invalid apps for available partners.
        invalid_apps_count = Application.include_invalid.filter(
            status__in=[Application.INVALID], partner__in=available_partners
        ).count()
        # count open apps for available partners.
        open_apps_count = Application.objects.filter(
            status__in=[
                Application.PENDING,
                Application.QUESTION,
                Application.APPROVED,
            ],
            partner__in=available_partners,
        ).count()
        # None of the following comparisons are going to be valid if we've bungled things and don't have open apps.
        self.assertGreater(open_apps_count, 0)

        # Change all available partners to bundle.
        for partner in available_partners:
            partner.authorization_method = Partner.BUNDLE
            partner.save()

        # recount invalid apps for available partners.
        post_save_invalid_apps_count = Application.include_invalid.filter(
            status__in=[Application.INVALID], partner__in=available_partners
        ).count()
        # recount open apps for available partners.
        post_save_open_apps_count = Application.objects.filter(
            status__in=[
                Application.PENDING,
                Application.QUESTION,
                Application.APPROVED,
            ],
            partner__in=available_partners,
        ).count()

        # We should have more invalid apps.
        self.assertGreater(post_save_invalid_apps_count, invalid_apps_count)
        # We should have fewer open apps
        self.assertLess(post_save_open_apps_count, open_apps_count)

        # None of those applications should be open now.
        self.assertEqual(post_save_open_apps_count, 0)

        # We should have gained the number of invalid apps that are no longer counted as open
        self.assertEqual(
            post_save_invalid_apps_count, invalid_apps_count + open_apps_count
        )


class BatchEditTest(TestCase):
    def setUp(self):
        super(BatchEditTest, self).setUp()
        self.url = reverse("applications:batch_edit")
        editor = EditorFactory()
        editor1 = EditorFactory()
        self.user = editor.user
        self.user1 = editor1.user

        coordinators = get_coordinators()
        coordinators.user_set.add(self.user)

        self.partner = PartnerFactory()
        self.partner1 = PartnerFactory()
        self.partner2 = PartnerFactory()
        self.stream = StreamFactory(accounts_available=None, partner=self.partner2)

        self.application = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=self.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.application1 = ApplicationFactory(
            editor=editor1,
            status=Application.PENDING,
            partner=self.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.application2 = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=self.partner1,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.application3 = ApplicationFactory(
            editor=editor1,
            status=Application.PENDING,
            partner=self.partner1,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.application4 = ApplicationFactory(
            editor=editor1,
            status=Application.PENDING,
            partner=self.partner2,
            specific_stream=self.stream,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.coordinator = UserFactory(username="coordinator")
        self.coordinator.set_password("coordinator")
        coordinators = get_coordinators()
        coordinators.user_set.add(self.coordinator)
        self.coordinator.userprofile.terms_of_use = True
        self.coordinator.userprofile.save()

        editor2 = EditorFactory()
        self.unpriv_user = editor2.user

        self.message_patcher = patch("TWLight.applications.views.messages.add_message")
        self.message_patcher.start()

    def tearDown(self):
        super(BatchEditTest, self).tearDown()
        self.message_patcher.stop()

    def test_missing_params_raise_http_bad_request(self):
        # Create a coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # No post data: bad.
        response = self.client.post(self.url, data={}, follow=True)
        self.assertEqual(response.status_code, 400)

        # Missing the 'batch_status' parameter: bad.
        response = self.client.post(self.url, data={"applications": 1}, follow=True)
        self.assertEqual(response.status_code, 400)

        # Has both parameters, but 'batch_status' has an invalid value: bad.

        assert 6 not in [
            Application.PENDING,
            Application.QUESTION,
            Application.APPROVED,
            Application.NOT_APPROVED,
            Application.INVALID,
        ]

        response = self.client.post(
            self.url, data={"applications": 1, "batch_status": 6}, follow=True
        )
        self.assertEqual(response.status_code, 400)

    def test_bogus_applications_parameter_handled(self):
        """
        If the applications parameter doesn't correspond to an existing
        application, the http request should succeed, but no apps should be
        changed.
        """

        # Check status quo ante.
        self.assertEqual(Application.objects.count(), 5)

        # Make sure that the batch_status value does *not* fail the request - we
        # want to be clear that we're testing the applications parameter.
        assert 3 in [
            Application.PENDING,
            Application.QUESTION,
            Application.APPROVED,
            Application.NOT_APPROVED,
            Application.INVALID,
        ]

        # Make sure the applications parameter actually is bogus.
        assert Application.objects.filter(pk=6).count() == 0

        # Create a coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Issue the request. Don't follow redirects from here.
        response = self.client.post(
            self.url, data={"applications": 2, "batch_status": 3}, follow=False
        )

        # Check things! We get redirected to the applications page when done.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, reverse("applications:list"))

        # No new apps created
        self.assertEqual(Application.objects.count(), 5)

        # Refresh object from db to check for changes (there shouldn't be any).
        app = Application.objects.get(pk=self.application.pk)

        self.assertEqual(app.editor, self.user.editor)
        self.assertEqual(app.partner, self.partner)
        self.assertEqual(app.status, Application.PENDING)
        self.assertEqual(app.rationale, "Just because")
        self.assertEqual(app.agreement_with_terms_of_use, True)

    def test_only_coordinators_can_batch_edit(self):
        # An anonymous user is prompted to login.
        response = self.client.post(
            self.url,
            data={"applications": self.application.pk, "batch_status": 3},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, settings.LOGIN_URL)

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)

        response = self.client.post(
            self.url,
            data={"applications": self.application.pk, "batch_status": 3},
            follow=False,
        )

        # An editor may not post to the page.
        self.assertEqual(response.status_code, 403)

        # Create a coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        response = self.client.post(
            self.url,
            data={"applications": self.application.pk, "batch_status": 3},
            follow=False,
        )

        # A coordinator may post to the page (on success, it redirects to the
        # application list page which they likely started on).
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, reverse("applications:list"))

    def test_sets_status(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.save()

        # Create a coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Approve the application.
        response = self.client.post(
            self.url,
            data={"applications": self.application.pk, "batch_status": 2},
            follow=False,
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.APPROVED)

    def test_sets_status_approved_for_variety_partners(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.save()

        self.partner.authorization_method = Partner.PROXY
        # Approval won't work if proxy partner is not available/waitlisted
        self.partner.status = Partner.AVAILABLE
        self.partner.accounts_available = 10
        self.partner.save()

        self.partner.coordinator = EditorCraftRoom(
            self, Terms=True, Coordinator=True
        ).user
        self.partner.save()
        self.partner1.coordinator = EditorCraftRoom(
            self, Terms=True, Coordinator=True
        ).user
        self.partner1.save()

        # Approve the applications
        response = self.client.post(
            self.url,
            data={
                "applications": [
                    self.application.pk,
                    self.application1.pk,
                    self.application2.pk,
                    self.application3.pk,
                ],
                "batch_status": 2,
            },
            follow=False,
        )

        # Two proxy partners
        # Approved applications are treated as sent for proxy partners
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.SENT)
        self.application1.refresh_from_db()
        self.assertEqual(self.application1.status, Application.SENT)
        self.application2.refresh_from_db()
        # Two non-proxy partners
        self.assertEqual(self.application2.status, Application.APPROVED)
        self.application3.refresh_from_db()
        self.assertEqual(self.application3.status, Application.APPROVED)

        # Testing auto-waitlisting once we run out of accounts for proxy partners
        self.partner.accounts_available = 4
        self.partner.save()

        self.application.status = Application.PENDING
        self.application.save()
        self.application1.status = Application.PENDING
        self.application1.save()

        self.assertEqual(self.partner.status, Partner.AVAILABLE)

        # Approve the application
        response = self.client.post(
            self.url,
            data={
                "applications": [self.application.pk, self.application1.pk],
                "batch_status": 2,
            },
            follow=False,
        )

        self.partner.refresh_from_db()
        self.assertEqual(self.partner.status, Partner.WAITLIST)

    def test_sets_status_approved_for_proxy_partners_with_streams(self):
        factory = RequestFactory()

        # For partners with collections we only care about the collection authorization method
        self.stream.authorization_method = Partner.PROXY
        self.stream.save()
        # Approval won't work if proxy partner is not available/waitlisted
        self.partner2.status = Partner.AVAILABLE
        self.partner2.accounts_available = 10
        self.partner2.save()

        self.partner2.coordinator = EditorCraftRoom(
            self, Terms=True, Coordinator=True
        ).user
        self.partner2.save()

        # Approve the applications
        response = self.client.post(
            self.url,
            data={"applications": self.application4.pk, "batch_status": 2},
            follow=False,
        )

        # Approved applications are treated as sent for proxy partners
        self.application4.refresh_from_db()
        self.assertEqual(self.application4.status, Application.SENT)

        # Our current setup allows either or workflow for accounts_available field,
        # and our code should be able to handle that
        self.partner2.accounts_available = None
        self.partner2.save()
        self.stream.accounts_available = 2
        self.stream.save()

        self.application4.status = Application.PENDING
        self.application4.save()

        # Approve the application
        response = self.client.post(
            self.url,
            data={"applications": self.application4.pk, "batch_status": 2},
            follow=False,
        )

        self.application4.refresh_from_db()
        self.assertEqual(self.application4.status, Application.SENT)

        self.partner2.status = Partner.WAITLIST
        self.partner2.save()

        self.application4.status = Application.PENDING
        self.application4.save()

        # Approve the application
        response = self.client.post(
            self.url,
            data={"applications": self.application4.pk, "batch_status": 2},
            follow=False,
        )

        self.application4.refresh_from_db()
        self.assertEqual(self.application4.status, Application.PENDING)

    def test_sets_days_open(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Approve the application
        response = self.client.post(
            self.url,
            data={
                "applications": self.application.pk,
                "batch_status": Application.APPROVED,
            },
            follow=True,
        )

        # Verify days open
        self.application.refresh_from_db()
        self.assertEqual(self.application.days_open, 3)

    def test_sets_date_closed(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Approve the application
        response = self.client.post(
            self.url,
            data={
                "applications": self.application.pk,
                "batch_status": Application.APPROVED,
            },
            follow=True,
        )

        # Verify date closed
        self.application.refresh_from_db()
        self.assertEqual(self.application.date_closed, date.today())

    def test_batch_edit_creates_authorization(self):
        # Make sure that if we batch edit, authorizations are created
        # as expected.
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Approve the application
        response = self.client.post(
            self.url,
            data={
                "applications": self.application.pk,
                "batch_status": Application.SENT,
            },
            follow=True,
        )

        authorization_exists = Authorization.objects.filter(
            user=self.application.user, partners=self.application.partner
        ).exists()

        self.assertTrue(authorization_exists)


class ListReadyApplicationsTest(TestCase):
    def test_no_proxy_bundle_partners(self):
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        proxy_partner = PartnerFactory(
            authorization_method=Partner.PROXY, coordinator=coordinator.user
        )
        bundle_partner = PartnerFactory(
            authorization_method=Partner.BUNDLE, coordinator=coordinator.user
        )
        other_partner1 = PartnerFactory(coordinator=coordinator.user)
        other_partner2 = PartnerFactory()
        ApplicationFactory(
            status=Application.APPROVED,  # This shouldn't be the case, but could happen in certain situations
            partner=proxy_partner,
        )
        ApplicationFactory(status=Application.APPROVED, partner=bundle_partner)
        ApplicationFactory(status=Application.APPROVED, partner=other_partner1)
        ApplicationFactory(status=Application.APPROVED, partner=other_partner2)

        request = RequestFactory().get(reverse("applications:send"))
        request.user = coordinator.user
        response = views.ListReadyApplicationsView.as_view()(request)
        self.assertNotEqual(
            set(response.context_data["object_list"]), {proxy_partner, bundle_partner}
        )
        self.assertEqual(set(response.context_data["object_list"]), {other_partner1})
        coordinator.user.is_superuser = True
        coordinator.user.save()
        request = RequestFactory().get(reverse("applications:send"))
        request.user = coordinator.user
        response = views.ListReadyApplicationsView.as_view()(request)
        self.assertNotEqual(
            set(response.context_data["object_list"]), {proxy_partner, bundle_partner}
        )
        self.assertEqual(
            set(response.context_data["object_list"]), {other_partner1, other_partner2}
        )


class MarkSentTest(TestCase):
    def setUp(self):
        super(MarkSentTest, self).setUp()
        editor = EditorFactory()
        self.user = editor.user

        coordinators = get_coordinators()
        coordinators.user_set.add(self.user)

        editor2 = EditorFactory()
        self.user2 = editor2.user
        editor3 = EditorFactory()
        self.user3 = editor3.user
        coordinators = get_coordinators()
        coordinators.user_set.add(self.user)
        coordinators.user_set.add(self.user3)

        self.partner = PartnerFactory(coordinator=self.user)

        self.partner2 = PartnerFactory()

        self.app1 = ApplicationFactory(
            editor=editor,
            status=Application.APPROVED,
            partner=self.partner,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.app2 = ApplicationFactory(
            editor=editor,
            status=Application.APPROVED,
            partner=self.partner2,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        editor2 = EditorFactory()
        self.unpriv_user = editor2.user

        self.url = reverse("applications:send_partner", kwargs={"pk": self.partner.pk})

        # Set up an access code to distribute
        self.access_code = AccessCode(code="ABCD-EFGH-IJKL", partner=self.partner)
        self.access_code.save()

        self.message_patcher = patch("TWLight.applications.views.messages.add_message")
        self.message_patcher.start()

    def tearDown(self):
        super(MarkSentTest, self).tearDown()
        self.message_patcher.stop()

    def test_invalid_params_raise_http_bad_request(self):
        # No post data: bad.
        request = RequestFactory().post(self.url, data={})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )
        self.assertEqual(response.status_code, 400)

        # Missing the 'applications' parameter: bad.
        request = RequestFactory().post(self.url, data={"bogus": 1})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )
        self.assertEqual(response.status_code, 400)

    def test_bogus_applications_parameter_handled(self):
        """
        If the applications parameter doesn't correspond to an existing
        application, the http request should succeed, but no apps should be
        changed.
        """
        # Check status quo ante.
        self.assertEqual(Application.objects.count(), 2)
        self.assertEqual(
            Application.objects.filter(status=Application.APPROVED).count(), 2
        )

        # Post a completely invalid app pk.
        request = RequestFactory().post(self.url, data={"applications": ["NaN"]})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )
        self.assertEqual(response.status_code, 400)

        self.app1.refresh_from_db()
        self.app2.refresh_from_db()
        self.assertEqual(self.app1.status, Application.APPROVED)
        self.assertEqual(self.app2.status, Application.APPROVED)

        # Post a valid app pk that doesn't correspond to the partner. That's
        # weird, but as long as we don't change anything's status it's fine.
        request = RequestFactory().post(self.url, data={"applications": [self.app2.pk]})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

        self.app1.refresh_from_db()
        self.app2.refresh_from_db()
        self.assertEqual(self.app1.status, Application.APPROVED)
        self.assertEqual(self.app2.status, Application.APPROVED)

        # Check that we've covered all existing apps with the above statements.
        self.assertEqual(Application.objects.count(), 2)

    def test_only_partner_coordinator_can_view(self):
        # Only the coordinator assigned to a specific partner should
        # be able to view that partner's send page.
        request = RequestFactory().get(self.url)

        # A coordinator who isn't assigned to this partner shouldn't be
        # able to view the page.
        request.user = self.user2
        with self.assertRaises(PermissionDenied):
            _ = views.SendReadyApplicationsView.as_view()(request, pk=self.partner.pk)

        # Whereas this partner's coordinator should.
        request.user = self.user
        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )
        self.assertEqual(response.status_code, 200)

    def test_only_coordinators_can_mark_sent(self):
        # An anonymous user is prompted to login.
        request = RequestFactory().post(self.url, data={"applications": [self.app2.pk]})
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            _ = views.SendReadyApplicationsView.as_view()(request, pk=self.partner.pk)

        # A user who is not a coordinator does not have access.
        coordinators = get_coordinators()
        coordinators.user_set.remove(self.unpriv_user)  # make sure
        request.user = self.unpriv_user

        with self.assertRaises(PermissionDenied):
            _ = views.SendReadyApplicationsView.as_view()(request, pk=self.partner.pk)

        # A coordinator may post to the page.
        coordinators.user_set.add(self.user)  # make sure
        request.user = self.user
        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )

        # Expected success condition: redirect back to the original page.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

    def test_restricted_applications_sent(self):
        # If a partner *only* has restricted applications, it shouldn't be
        # listed on the Send page. If a partner has at least one
        # non-restricted application, it should be there.
        request = RequestFactory().get(reverse("applications:send"))
        request.user = self.user

        editor_restricted = EditorFactory()
        self.restricted_user = editor_restricted.user
        restricted = get_restricted()
        self.restricted_user.groups.add(restricted)
        self.restricted_user.save()

        self.app_restricted = ApplicationFactory(
            editor=editor_restricted,
            status=Application.APPROVED,
            partner=self.partner2,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        partner3 = PartnerFactory(coordinator=self.user)

        app_restricted2 = ApplicationFactory(
            editor=editor_restricted,
            status=Application.APPROVED,
            partner=partner3,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.partner2.coordinator = self.user
        self.partner2.save()

        response = views.ListReadyApplicationsView.as_view()(request)
        content = response.render().content.decode("utf-8")
        self.assertIn(escape(self.partner2.company_name), content)
        self.assertNotIn(escape(partner3.company_name), content)

    def test_restricted_applications_mark_sent(self):
        # Applications from restricted users shouldn't be listed
        # on the send page.
        request = RequestFactory().get(
            reverse("applications:send_partner", kwargs={"pk": self.partner2.pk})
        )
        request.user = self.user

        editor_restricted = EditorFactory()
        self.restricted_user = editor_restricted.user
        restricted = get_restricted()
        self.restricted_user.groups.add(restricted)
        self.restricted_user.save()

        app_restricted = ApplicationFactory(
            editor=editor_restricted,
            status=Application.APPROVED,
            partner=self.partner2,
            rationale="Just because",
            agreement_with_terms_of_use=True,
        )

        self.partner2.coordinator = self.user
        self.partner2.save()

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner2.pk
        )
        content = response.render().content.decode("utf-8")

        self.assertIn(escape(self.app2.editor.wp_username), content)
        self.assertNotIn(escape(app_restricted.editor.wp_username), content)

    def test_access_codes_sent(self):
        # For access code partners, coordinators assign a code to an
        # application rather than simply marking it sent.

        self.partner.authorization_method = Partner.CODES
        self.partner.save()

        request = RequestFactory().post(
            self.url,
            data={
                "accesscode": [
                    "{app_pk}_{code}".format(
                        app_pk=self.app1.pk, code=self.access_code.code
                    )
                ]
            },
        )
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )

        # Expected success condition: redirect back to the original page.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

    def test_email_authorization_method(self):
        # If partner's authroization method is EMAIL
        # then partner's 'mark as sent' page should
        # display list of approved applications

        self.partner.authorization_method = Partner.EMAIL
        self.partner.save()

        request = RequestFactory().get(self.url)
        request.user = self.user
        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk
        )

        # Expected success condition: coordinator may access the page
        self.assertEqual(response.status_code, 200)

    def test_proxy_authorization_method(self):
        # If partner's authroization method is PROXY
        # then partner's 'mark as sent' page should raise 404

        self.partner.authorization_method = Partner.PROXY
        self.partner.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        # Expected success condition: raise a 404 not found page
        with self.assertRaises(Http404):
            _ = views.SendReadyApplicationsView.as_view()(request, pk=self.partner.pk)
