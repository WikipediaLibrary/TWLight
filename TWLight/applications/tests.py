# -*- coding: utf-8 -*-
from datetime import date, timedelta
from itertools import chain
from mock import patch
import reversion
from urlparse import urlparse

from django import forms
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import models
from django.test import TestCase, Client, RequestFactory

from TWLight.resources.models import Partner, Stream
from TWLight.resources.factories import PartnerFactory, StreamFactory
from TWLight.resources.tests import EditorCraftRoom
from TWLight.users.factories import EditorFactory, UserFactory
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Editor

from . import views
from .helpers import (USER_FORM_FIELDS,
                      PARTNER_FORM_OPTIONAL_FIELDS,
                      FIELD_TYPES,
                      SPECIFIC_STREAM,
                      SPECIFIC_TITLE,
                      AGREEMENT_WITH_TERMS_OF_USE,
                      REAL_NAME,
                      COUNTRY_OF_RESIDENCE,
                      OCCUPATION,
                      AFFILIATION,
                      get_output_for_application)
from .factories import ApplicationFactory
from .forms import BaseApplicationForm
from .models import Application


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
        return list(set(chain.from_iterable(
            (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
            for field in model._meta.get_fields()
            if not (field.many_to_one and field.related_model is None)
        )))

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
                isinstance(Partner._meta.get_field(field),
                    models.BooleanField))


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
            if not isinstance(Application._meta.get_field(field),
                    models.BooleanField):
                self.assertTrue(Application._meta.get_field(field).blank)
            else:
                self.assertFalse(Application._meta.get_field(field).default)

            # Make sure the form fields we're using match what the model fields
            # can record.
            modelfield = Application._meta.get_field(field)
            formfield = modelfield.formfield()

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
            if not isinstance(Editor._meta.get_field(field),
                    models.BooleanField):
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
        setattr(editor, REAL_NAME, 'Alice')
        setattr(editor, COUNTRY_OF_RESIDENCE, 'Holy Roman Empire')
        setattr(editor, OCCUPATION, 'Dog surfing instructor')
        setattr(editor, AFFILIATION, 'The Long Now Foundation')
        setattr(editor, 'wp_username', 'wp_alice')
        setattr(editor, 'home_wiki', 'en')
        setattr(editor, 'email', 'alice@example.com')
        editor.save()

        partner = Partner()
        for field in USER_FORM_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS:
            setattr(partner, field, True)
        partner.terms_of_use = 'https://example.com/terms'
        partner.save()

        stream = Stream()
        stream.partner = partner
        stream.name = 'Stuff and things'
        stream.save()

        app = ApplicationFactory(status=Application.APPROVED,
            partner=partner,
            editor=editor,
            rationale='just because',
            comments='nope')
        setattr(app, AGREEMENT_WITH_TERMS_OF_USE, True)
        setattr(app, SPECIFIC_STREAM, stream)
        setattr(app, SPECIFIC_TITLE, 'Alice in Wonderland')
        app.save()

        app.refresh_from_db()

        output = get_output_for_application(app)
        self.assertEqual(output[REAL_NAME], 'Alice')
        self.assertEqual(output[COUNTRY_OF_RESIDENCE], 'Holy Roman Empire')
        self.assertEqual(output[OCCUPATION], 'Dog surfing instructor')
        self.assertEqual(output[AFFILIATION], 'The Long Now Foundation')
        self.assertEqual(output[SPECIFIC_STREAM], stream)
        self.assertEqual(output[SPECIFIC_TITLE], 'Alice in Wonderland')
        self.assertEqual(output['Email'], 'alice@example.com')
        self.assertEqual(output[AGREEMENT_WITH_TERMS_OF_USE], True)

        # Make sure that in enumerating the keys we didn't miss any (e.g. if
        # the codebase changes).
        self.assertEqual(8, len(output.keys()))



    def test_application_output_2(self):
        """
        Case 2, we'll test an application where a partner requires none of the
        optional fields.
        """
        editor = EditorFactory()
        setattr(editor, 'wp_username', 'wp_alice')
        setattr(editor, 'home_wiki', 'en')
        setattr(editor, 'email', 'alice@example.com')
        editor.save()

        partner = Partner()
        for field in USER_FORM_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS:
            setattr(partner, field, False)
        partner.save()

        app = ApplicationFactory(status=Application.APPROVED,
            partner=partner,
            editor=editor,
            rationale='just because',
            comments='nope')
        app.agreement_with_terms_of_use = False
        app.save()

        app.refresh_from_db()

        output = get_output_for_application(app)
        self.assertEqual(output['Email'], 'alice@example.com')

        # Make sure that in enumerating the keys we didn't miss any (e.g. if
        # the codebase changes).
        self.assertEqual(1, len(output.keys()))


    def test_application_output_3(self):
        """
        Case 3, we'll test an application where a partner requires some but not
        all of the optional fields.
        """
        editor = EditorFactory()
        setattr(editor, REAL_NAME, 'Alice')
        setattr(editor, COUNTRY_OF_RESIDENCE, 'Holy Roman Empire')
        setattr(editor, OCCUPATION, 'Dog surfing instructor')
        setattr(editor, AFFILIATION, 'The Long Now Foundation')
        setattr(editor, 'wp_username', 'wp_alice')
        setattr(editor, 'home_wiki', 'en')
        setattr(editor, 'email', 'alice@example.com')
        editor.save()

        partner = Partner()
        for field in PARTNER_FORM_OPTIONAL_FIELDS:
            setattr(partner, field, False)
        for field in USER_FORM_FIELDS:
            setattr(partner, field, True)
        partner.save()

        app = ApplicationFactory(status=Application.APPROVED,
            partner=partner,
            editor=editor,
            rationale='just because',
            comments='nope')
        app.agreement_with_terms_of_use = False
        app.save()

        app.refresh_from_db()

        output = get_output_for_application(app)
        self.assertEqual(output[REAL_NAME], 'Alice')
        self.assertEqual(output[COUNTRY_OF_RESIDENCE], 'Holy Roman Empire')
        self.assertEqual(output[OCCUPATION], 'Dog surfing instructor')
        self.assertEqual(output[AFFILIATION], 'The Long Now Foundation')
        self.assertEqual(output['Email'], 'alice@example.com')

        # Make sure that in enumerating the keys we didn't miss any (e.g. if
        # the codebase changes).
        self.assertEqual(5, len(output.keys()))



class BaseApplicationViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseApplicationViewTest, cls).setUpClass()
        cls.client = Client()

        # Note: not an Editor.
        cls.base_user = UserFactory(username='base_user')
        cls.base_user.set_password('base_user')
        cls.base_user.userprofile.terms_of_use = True
        cls.base_user.userprofile.save()

        cls.editor = UserFactory(username='editor')
        EditorFactory(user=cls.editor)
        cls.editor.set_password('editor')
        cls.editor.userprofile.terms_of_use = True
        cls.editor.userprofile.save()

        cls.editor2 = UserFactory(username='editor2')
        EditorFactory(user=cls.editor2)
        cls.editor2.set_password('editor2')
        cls.editor2.userprofile.terms_of_use = True
        cls.editor2.userprofile.save()

        cls.coordinator = UserFactory(username='coordinator')
        cls.coordinator.set_password('coordinator')
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)
        cls.coordinator.userprofile.terms_of_use = True
        cls.coordinator.userprofile.save()

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch('TWLight.applications.views.messages.add_message')
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
        cls.url = reverse('applications:request')


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
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.pk]

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
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.pk]
        user = UserFactory()
        user.userprofile.terms_of_use = True
        user.userprofile.save()
        _ = EditorFactory(user=user)
        request.user = user

        # Case 1: no email; access should be denied.
        user.email = ''
        user.save()
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)

        # Case 2: user has email; access should be allowed.
        user.email = 'foo@bar.com'
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
        user.email = ''
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

        fieldkey = 'partner_{id}'.format(id=partner.id)
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
            'partner_{id}'.format(id=p1.id): True,
            'partner_{id}'.format(id=p2.id): False,
        }


        factory = RequestFactory()
        request = factory.post(self.url, data=data)
        request.user = self.editor
        request.session = {}
        response = views.RequestApplicationView.as_view()(request)

        self.assertEqual(response.url, 
            reverse('applications:apply'))


    def test_valid_form_writes_session_key(self):
        """
        Users who submit a valid form generate a matching session key.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        data = {
            'partner_{id}'.format(id=p1.id): True,
            'partner_{id}'.format(id=p2.id): False,
        }
        request = self._get_request_with_session(data)
        self.assertEqual(request.session[views.PARTNERS_SESSION_KEY], [p1.id])

        data = {
            'partner_{id}'.format(id=p1.id): False,
            'partner_{id}'.format(id=p2.id): True,
        }
        request = self._get_request_with_session(data)
        self.assertEqual(request.session[views.PARTNERS_SESSION_KEY], [p2.id])

        data = {
            'partner_{id}'.format(id=p1.id): True,
            'partner_{id}'.format(id=p2.id): True,
        }
        request = self._get_request_with_session(data)

        # Since we don't care which order the IDs are in, but list comparison
        # is sensitive to order, let's check first that both lists have the
        # same elements, and second that they are of the same length.
        self.assertEqual(set(request.session[views.PARTNERS_SESSION_KEY]),
            set([p2.id, p1.id]))
        self.assertEqual(len(request.session[views.PARTNERS_SESSION_KEY]),
            len([p2.id, p1.id]))



class SubmitApplicationTest(BaseApplicationViewTest):
    @classmethod
    def setUpClass(cls):
        super(SubmitApplicationTest, cls).setUpClass()
        cls.url = reverse('applications:apply')


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
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.pk]

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


    def test_missing_session_key(self):
        """
        If the PARTNERS_SESSION_KEY is missing, the view should redirect to
        RequestApplicationView.
        """

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        session = self.client.session
        if views.PARTNERS_SESSION_KEY in session.keys():
            del session[views.PARTNERS_SESSION_KEY]

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        response_path = urlparse(response.url).path
        self.assertEqual(response_path, reverse('applications:request'))


    def test_empty_session_key(self):
        """
        If the PARTNERS_SESSION_KEY is an empty list, the view should redirect
        to RequestApplicationView.
        """
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.editor
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = []

        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('applications:request'))


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
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = ['cats']
        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('applications:request'))

        # Invalid pk: no such Partner
        self.assertEqual(Partner.objects.filter(pk=4500).count(), 0)

        request.session[views.PARTNERS_SESSION_KEY] = [1, 4500]
        response = views.SubmitApplicationView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('applications:request'))


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
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.pk]

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
            agreement_with_terms_of_use=False
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}

        form = view.get_form(BaseApplicationForm)

        # Check user data.
        self.assertIn('real_name', form.fields)
        self.assertIn('country_of_residence', form.fields)
        self.assertNotIn('occupation', form.fields)
        self.assertNotIn('affiliation', form.fields)

        # Check partner data: p1.
        self.assertNotIn('partner_{id}_specific_stream'.format(
            id=p1.id), form.fields)
        self.assertNotIn('partner_{id}_specific_title'.format(
            id=p1.id), form.fields)
        self.assertNotIn('partner_{id}_agreement_with_terms_of_use'.format(
            id=p1.id), form.fields)
        self.assertIn('partner_{id}_rationale'.format(
            id=p1.id), form.fields)
        self.assertIn('partner_{id}_comments'.format(
            id=p1.id), form.fields)


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
            agreement_with_terms_of_use=False
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
            agreement_with_terms_of_use=False
        )

        # Test just p1.
        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        form = view.get_form(BaseApplicationForm)

        # Check user data.
        self.assertIn('real_name', form.fields)
        self.assertIn('country_of_residence', form.fields)
        self.assertNotIn('occupation', form.fields)
        self.assertNotIn('affiliation', form.fields)

        # Check partner data: p1.
        self.assertNotIn('partner_{id}_specific_stream'.format(
            id=p1.id), form.fields)
        self.assertNotIn('partner_{id}_specific_title'.format(
            id=p1.id), form.fields)
        self.assertNotIn('partner_{id}_agreement_with_terms_of_use'.format(
            id=p1.id), form.fields)
        self.assertIn('partner_{id}_rationale'.format(
            id=p1.id), form.fields)
        self.assertIn('partner_{id}_comments'.format(
            id=p1.id), form.fields)

        # Check partner data: p2.
        self.assertNotIn('partner_{id}_specific_stream'.format(
            id=p2.id), form.fields)
        self.assertNotIn('partner_{id}_specific_title'.format(
            id=p2.id), form.fields)
        self.assertNotIn('partner_{id}_agreement_with_terms_of_use'.format(
            id=p2.id), form.fields)
        self.assertIn('partner_{id}_rationale'.format(
            id=p2.id), form.fields)
        self.assertIn('partner_{id}_comments'.format(
            id=p2.id), form.fields)

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
            agreement_with_terms_of_use=False
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
            agreement_with_terms_of_use=False
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        form = view.get_form(BaseApplicationForm)

        # Check user data.
        self.assertIn('real_name', form.fields)
        self.assertIn('country_of_residence', form.fields)
        self.assertIn('occupation', form.fields)
        self.assertNotIn('affiliation', form.fields)

        # Check partner data: p1.
        self.assertNotIn('partner_{id}_specific_stream'.format(
            id=p1.id), form.fields)
        self.assertNotIn('partner_{id}_specific_title'.format(
            id=p1.id), form.fields)
        self.assertNotIn('partner_{id}_agreement_with_terms_of_use'.format(
            id=p1.id), form.fields)
        self.assertIn('partner_{id}_rationale'.format(
            id=p1.id), form.fields)
        self.assertIn('partner_{id}_comments'.format(
            id=p1.id), form.fields)

        # Check partner data: p2.
        self.assertNotIn('partner_{id}_specific_stream'.format(
            id=p2.id), form.fields)
        self.assertIn('partner_{id}_specific_title'.format(
            id=p2.id), form.fields)
        self.assertNotIn('partner_{id}_agreement_with_terms_of_use'.format(
            id=p2.id), form.fields)
        self.assertIn('partner_{id}_rationale'.format(
            id=p2.id), form.fields)
        self.assertIn('partner_{id}_comments'.format(
            id=p2.id), form.fields)


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
            agreement_with_terms_of_use=False
        )

        user = UserFactory(username='alice')
        if hasattr(user, 'editor'):
            user.editor.delete()

        EditorFactory(
            user=user,
            # Same as the factory defaults, but repeated here because explicit
            # is better than implicit - let's make it obvious that our
            # assertEquals ought to be true.
            real_name = 'Alice Crypto',
            occupation = 'Cat floofer',
            # This is different from the default, because we should make sure to
            # check an empty string.
            affiliation = '',
            # This is different from the default, because we should make sure to
            # check something Unicodey.
            country_of_residence = 'Ümláuttøwñ',
        )

        view = self._get_isolated_view(views.SubmitApplicationView, user)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}

        initial = view.get_initial()
        self.assertEqual(initial['real_name'], 'Alice Crypto')
        self.assertEqual(initial['country_of_residence'], 'Ümláuttøwñ')
        self.assertEqual(initial['occupation'], 'Cat floofer')
        self.assertEqual(initial['affiliation'], '')

        user.delete()


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
            agreement_with_terms_of_use=False
        )

        factory = RequestFactory()

        data = {
            'real_name': 'Anonymous Coward',
            'partner_{id}_rationale'.format(id=p1.id): 'Whimsy',
            'partner_{id}_comments'.format(id=p1.id): 'None whatsoever',
        }

        request = factory.post(self.url, data)
        request.user = self.editor
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.id]

        response = views.SubmitApplicationView.as_view()(request)

        expected_url = reverse('users:editor_detail',
                                kwargs={'pk': self.editor.editor.pk})
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
            agreement_with_terms_of_use=False
        )

        user = UserFactory()

        EditorFactory(
            user=user,
            # All 3 of these fields will be required by PartnerFactory.
            real_name='',
            country_of_residence='Lithuania',
            occupation='Cat floofer',
        )

        data = {
            # Should fill in existing blank field.
            'real_name': 'Anonymous Coward',
            # Should update existing not-blank field.
            'country_of_residence': 'Bolivia',
            # Should result in no change.
            'occupation': 'Cat floofer',
            'partner_{id}_rationale'.format(id=p1.id): 'Whimsy',
            'partner_{id}_comments'.format(id=p1.id): 'None whatsoever',
        }

        factory = RequestFactory()

        request = factory.post(self.url, data)
        request.user = user
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.id]

        _ = views.SubmitApplicationView.as_view()(request)
        editor = user.editor
        editor.refresh_from_db()

        self.assertEqual(editor.real_name, 'Anonymous Coward')
        self.assertEqual(editor.country_of_residence, 'Bolivia')
        self.assertEqual(editor.occupation, 'Cat floofer')

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
            agreement_with_terms_of_use=False
        )
        p2 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=False,
            specific_stream=True,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False
        )

        s1 = Stream()
        s1.partner = p2
        s1.name = 'Health and Biological Sciences'
        s1.save()

        # Checking our assumptions, just in case. This means that our
        # get() queries later on should not raise MultipleObjectsReturned.
        self.assertEqual(Application.objects.filter(partner=p1).count(), 0)
        self.assertEqual(Application.objects.filter(partner=p2).count(), 0)

        factory = RequestFactory()

        data = {
            'partner_{id}_rationale'.format(id=p1.id): 'Whimsy',
            'partner_{id}_comments'.format(id=p1.id): 'None whatsoever',
            'partner_{id}_specific_title'.format(id=p1.id): 'Open Access for n00bs',
            'partner_{id}_rationale'.format(id=p2.id): 'Saving the world',
            'partner_{id}_comments'.format(id=p2.id): '',
            'partner_{id}_specific_stream'.format(id=p2.id): s1.pk,
        }

        request = factory.post(self.url, data)
        request.user = self.editor
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.id, p2.id]

        _ = views.SubmitApplicationView.as_view()(request)

        # If the application has not been created, these lines will raise
        # DoesNotExist.
        app1 = Application.objects.get(partner=p1, editor=self.editor.editor)
        app2 = Application.objects.get(partner=p2, editor=self.editor.editor)

        # Make sure applications have the expected properties, based on the
        # partner requirements and submitted data.
        self.assertEqual(app1.status, Application.PENDING)
        self.assertEqual(app1.rationale, 'Whimsy')
        self.assertEqual(app1.comments, 'None whatsoever')
        self.assertEqual(app1.specific_title, 'Open Access for n00bs')
        self.assertEqual(app1.specific_stream, None)
        self.assertEqual(app1.agreement_with_terms_of_use, False)

        self.assertEqual(app2.status, Application.PENDING)
        self.assertEqual(app2.rationale, 'Saving the world')
        self.assertEqual(app2.comments, '')
        self.assertEqual(app2.specific_title, '')
        self.assertEqual(app2.specific_stream, s1)
        self.assertEqual(app2.agreement_with_terms_of_use, False)


    def test_get_partners(self):
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        # We need to coerce the querysets to a list for the comparison to
        # work; assertQuerysetEqual on the underlying querysets fails. I'm going
        # to guess that one of the querysets is lazy and one isn't, so we have
        # to force evaluation for equality to work?
        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id]}
        self.assertListEqual(list(view._get_partners()),
            list(Partner.objects.filter(pk=p1.id)))

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p2.id]}
        self.assertListEqual(list(view._get_partners()),
            list(Partner.objects.filter(pk=p2.id)))

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}
        self.assertListEqual(list(view._get_partners()),
            list(Partner.objects.filter(pk__in=[p1.id, p2.id])))


    def test_get_partner_fields(self):

        p1 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=True,
            specific_stream=False,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=True,
        )
        p2 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=False,
            specific_stream=True,
            occupation=False,
            affiliation=False,
            agreement_with_terms_of_use=False
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        # Use set(), because order is unimportant.
        self.assertEqual(set(view._get_partner_fields(p1)),
            set(['specific_title', 'agreement_with_terms_of_use']))

        self.assertEqual(set(view._get_partner_fields(p2)),
            set(['specific_stream']))


    def test_get_user_fields(self):

        p1 = PartnerFactory(
            real_name=False,
            country_of_residence=False,
            specific_title=True,
            specific_stream=False,
            occupation=True,
            affiliation=True,
            agreement_with_terms_of_use=True,
        )
        p2 = PartnerFactory(
            real_name=True,
            country_of_residence=False,
            specific_title=False,
            specific_stream=True,
            occupation=True,
            affiliation=False,
            agreement_with_terms_of_use=False
        )

        view = self._get_isolated_view(views.SubmitApplicationView)
        view.request.session = {views.PARTNERS_SESSION_KEY: [p1.id, p2.id]}

        partners = Partner.objects.filter(pk__in=[p1.pk, p2.pk])

        self.assertEqual(set(view._get_user_fields(partners)),
            set(['real_name', 'occupation', 'affiliation']))



class ListApplicationsTest(BaseApplicationViewTest):

    @classmethod
    def setUpClass(cls):
        super(ListApplicationsTest, cls).setUpClass()
        cls.superuser = User.objects.create_user(
            username='super', password='super')
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

        # Make sure there are some up-for-renewal querysets, too.
        ApplicationFactory(status=Application.PENDING, parent=parent)
        ApplicationFactory(status=Application.QUESTION, parent=parent)
        ApplicationFactory(status=Application.APPROVED, parent=parent)
        ApplicationFactory(status=Application.NOT_APPROVED, parent=parent)
        ApplicationFactory(status=Application.SENT, parent=parent)


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
        request.session = {}
        request.session[views.PARTNERS_SESSION_KEY] = [p1.pk]

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
        response = view.as_view()(request)

        for obj in queryset:
            # Unlike Client(), RequestFactory() doesn't render the response;
            # we'll have to do that before we can check for its content.
            self.assertIn(obj.__str__(), response.render().content)


    def test_list_authorization(self):
        url = reverse('applications:list')
        self._base_test_authorization(url, views.ListApplicationsView)


    def test_list_object_visibility(self):
        url = reverse('applications:list')
        queryset = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION])
        self._base_test_object_visibility(url, views.ListApplicationsView, queryset)


    def test_list_approved_authorization(self):
        url = reverse('applications:list_approved')
        self._base_test_authorization(url, views.ListApprovedApplicationsView)


    def test_list_approved_object_visibility(self):
        url = reverse('applications:list_approved')
        queryset = Application.objects.filter(
            status=Application.APPROVED)
        self._base_test_object_visibility(url,
            views.ListApprovedApplicationsView, queryset)


    def test_list_rejected_authorization(self):
        url = reverse('applications:list_rejected')
        self._base_test_authorization(url, views.ListRejectedApplicationsView)


    def test_list_rejected_object_visibility(self):
        url = reverse('applications:list_rejected')
        queryset = Application.objects.filter(
            status=Application.NOT_APPROVED)
        self._base_test_object_visibility(url,
            views.ListRejectedApplicationsView, queryset)


    def test_list_expiring_queryset(self):
        url = reverse('applications:list_expiring')

        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.coordinator

        response = views.ListExpiringApplicationsView.as_view()(request)

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION],
            parent__isnull=False)
        template_qs = response.context_data['object_list']

        # See comment on test_queryset_unfiltered.
        self.assertEqual(sorted([item.pk for item in expected_qs]),
                         sorted([item.pk for item in template_qs]))


    def test_queryset_unfiltered(self):
        """
        Make sure that ListApplicationsView has the correct queryset in context
        when no filters are applied.
        """
        url = reverse('applications:list')

        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.coordinator

        response = views.ListApplicationsView.as_view()(request)

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION])
        template_qs = response.context_data['object_list']

        # We can't use assertQuerysetEqual, because the one returned by the view
        # is ordered and this one is not. (Testing order is not important here.)
        # And simply using sorted() (or sorted(list())) on the querysets is
        # mysteriously unreliable. So we'll grab the pks of each queryset,
        # sort them, and compare *those*. This is equivalent, semantically, to
        # what we actually want ('are the same items in both querysets').
        self.assertEqual(sorted([item.pk for item in expected_qs]),
                         sorted([item.pk for item in template_qs]))


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

        ApplicationFactory(status=Application.PENDING,
                           partner=new_partner,
                           editor=new_editor)

        url = reverse('applications:list')
        self.client.login(username='coordinator', password='coordinator')

        return new_editor, new_partner, url


    def test_queryset_filtered_case_1(self):
        """
        List is filtered by an editor.
        """
        new_editor, _, url = self._test_queryset_filtered_base()

        factory = RequestFactory()
        request = factory.post(url, {'editor': new_editor.pk})
        request.user = self.coordinator

        response = views.ListApplicationsView.as_view()(request)

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION],
            editor=new_editor)
        template_qs = response.context_data['object_list']

        self.assertEqual(sorted([item.pk for item in expected_qs]),
                         sorted([item.pk for item in template_qs]))


    def test_queryset_filtered_case_2(self):
        """
        List is filtered by a partner.
        """
        _, new_partner, url = self._test_queryset_filtered_base()

        factory = RequestFactory()
        request = factory.post(url, {'partner': new_partner.pk})
        request.user = self.coordinator

        response = views.ListApplicationsView.as_view()(request)

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION],
            partner=new_partner)
        template_qs = response.context_data['object_list']

        self.assertEqual(sorted([item.pk for item in expected_qs]),
                         sorted([item.pk for item in template_qs]))


    def test_queryset_filtered_case_3(self):
        """
        List is filtered by both editor and partner.
        """
        new_editor, new_partner, url = self._test_queryset_filtered_base()

        factory = RequestFactory()
        request = factory.post(url,
            {'editor': new_editor.pk, 'partner': new_partner.pk})
        request.user = self.coordinator

        response = views.ListApplicationsView.as_view()(request)

        expected_qs = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION],
            editor=new_editor,
            partner=new_partner)
        template_qs = response.context_data['object_list']

        self.assertEqual(sorted([item.pk for item in expected_qs]),
                         sorted([item.pk for item in template_qs]))


    def test_invalid_editor_post_handling(self):
        _, _, url = self._test_queryset_filtered_base()

        # Check assumption.
        self.assertFalse(Editor.objects.filter(pk=500))
        request = RequestFactory().post(url,
            data={'editor': 500})
        request.user = self.coordinator

        with self.assertRaises(Editor.DoesNotExist):
            _ = views.ListApplicationsView.as_view()(request)


    def test_invalid_partner_post_handling(self):
        _, _, url = self._test_queryset_filtered_base()

        # Check assumption.
        self.assertFalse(Partner.objects.filter(pk=500))
        request = RequestFactory().post(url,
            data={'partner': 500})
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
        url = reverse('applications:list')
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {'partner': new_partner.pk})
        request.user = self.coordinator

        instance = views.ListApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_2(self):
        """
        Case 2 is ListApplicationsView / get.
        """
        url = reverse('applications:list')
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_3(self):
        """
        Case 3 is ListApprovedApplicationsView / post.
        """
        url = reverse('applications:list_approved')
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {'partner': new_partner.pk})
        request.user = self.coordinator

        instance = views.ListApprovedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_4(self):
        """
        Case 4 is ListApprovedApplicationsView / get.
        """
        url = reverse('applications:list_rejected')
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListApprovedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_5(self):
        """
        Case 5 is ListRejectedApplicationsView / post.
        """
        url = reverse('applications:list_rejected')
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {'partner': new_partner.pk})
        request.user = self.coordinator

        instance = views.ListRejectedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_6(self):
        """
        Case 4 is ListRejectedApplicationsView / get.
        """
        url = reverse('applications:list_rejected')
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListRejectedApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_7(self):
        """
        Case 7 is ListExpiringApplicationsView / post.
        """
        url = reverse('applications:list_expiring')
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {'partner': new_partner.pk})
        request.user = self.coordinator

        instance = views.ListExpiringApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_8(self):
        """
        Case 8 is ListExpiringApplicationsView / get.
        """
        url = reverse('applications:list_expiring')
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListExpiringApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_9(self):
        """
        Case 9 is ListSentApplicationsView / post.
        """
        url = reverse('applications:list_expiring')
        new_partner = PartnerFactory()

        request = RequestFactory().post(url, {'partner': new_partner.pk})
        request.user = self.coordinator

        instance = views.ListSentApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))


    def test_ensure_object_list_exists_case_10(self):
        """
        Case 10 is ListSentApplicationsView / get.
        """
        url = reverse('applications:list_expiring')
        request = RequestFactory().get(url)
        request.user = self.coordinator

        instance = views.ListSentApplicationsView()
        instance.request = request
        instance.get_context_data()

        self.assertTrue(hasattr(instance, 'object_list'))



class RenewApplicationTest(BaseApplicationViewTest):
    def test_protected_to_self_only(self):
        partner = PartnerFactory(renewals_available=True)
        app = ApplicationFactory(partner=partner,
            status=Application.APPROVED, editor=self.editor.editor)

        request = RequestFactory().get(reverse('applications:renew',
            kwargs={'pk': app.pk}))
        request.user = self.editor

        response = views.RenewApplicationView.as_view()(
            request, pk=app.pk)

        # It redirects to the user's home on success.
        self.assertEqual(response.status_code, 302)

        user2 = UserFactory()
        request.user = user2

        with self.assertRaises(PermissionDenied):
            _ = views.RenewApplicationView.as_view()(
                request, pk=app.pk)


    def test_getting_url_renews_app(self):
        partner = PartnerFactory(renewals_available=True)
        app = ApplicationFactory(partner=partner,
            status=Application.APPROVED, editor=self.editor.editor)

        self.assertTrue(app.is_renewable) # check assumption

        request = RequestFactory().get(reverse('applications:renew',
            kwargs={'pk': app.pk}))
        request.user = self.editor

        _ = views.RenewApplicationView.as_view()(
            request, pk=app.pk)

        app.refresh_from_db()
        self.assertFalse(app.is_renewable)
        self.assertTrue(Application.objects.filter(parent=app))



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


    def test_earliest_expiry_date_set_on_save(self):
        app = ApplicationFactory()
        self.assertFalse(app.earliest_expiry_date)

        app.date_closed = date.today()
        app.save()

        term = app.partner.access_grant_term
        expected_expiry = app.date_created + term

        self.assertEqual(app.earliest_expiry_date, expected_expiry)


    def test_bootstrap_class(self):
        app = ApplicationFactory(status=Application.PENDING)
        self.assertEqual(app.get_bootstrap_class(), '-primary')

        app.status = Application.QUESTION
        app.save()
        self.assertEqual(app.get_bootstrap_class(), '-warning')

        app.status = Application.APPROVED
        app.save()
        self.assertEqual(app.get_bootstrap_class(), '-success')

        app.status = Application.NOT_APPROVED
        app.save()
        self.assertEqual(app.get_bootstrap_class(), '-danger')


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
            status=Application.PENDING,
            rationale='for great justice')

        orig_version = app.get_latest_version()
        self.assertTrue(isinstance(orig_version,
            reversion.models.Version))

        self.assertEqual(orig_version.field_dict['status'], Application.PENDING)
        self.assertEqual(orig_version.field_dict['rationale'], 'for great justice')

        app.status = Application.QUESTION
        app.save()

        new_version = app.get_latest_version()
        self.assertTrue(isinstance(new_version,
            reversion.models.Version))
        self.assertEqual(new_version.field_dict['status'], Application.QUESTION)
        self.assertEqual(new_version.field_dict['rationale'], 'for great justice')


    def test_get_latest_revision(self):
        app = ApplicationFactory()

        orig_revision = app.get_latest_revision()
        self.assertTrue(isinstance(orig_revision,
            reversion.models.Revision))

        app.status = Application.QUESTION
        app.save()

        new_revision = app.get_latest_revision()
        self.assertTrue(isinstance(new_revision,
            reversion.models.Revision))
        self.assertNotEqual(orig_revision, new_revision)


    def test_get_is_probably_expired(self):
        app = ApplicationFactory()

        # Apps do not have expiry dates when set (as the expiry date is
        # calculated from the date of approval), so they can't be expired.
        self.assertFalse(app.is_probably_expired())

        # It should now have an expiration date, but this defaults to a year
        # in the future, so the access grant should not have expired.
        app.status = Application.APPROVED
        app.save()
        self.assertTrue(app.is_probably_expired is not None)
        self.assertFalse(app.is_probably_expired())

        app.earliest_expiry_date = date.today() - timedelta(days=1)
        app.save()
        self.assertTrue(app.is_probably_expired())


    def test_get_num_days_since_expiration(self):
        app = ApplicationFactory()
        self.assertTrue(app.get_num_days_since_expiration() is None)

        app.earliest_expiry_date = date.today()
        app.save()
        self.assertEqual(app.get_num_days_since_expiration(), 0)

        app.earliest_expiry_date = date.today() + timedelta(days=1)
        app.save()
        self.assertTrue(app.get_num_days_since_expiration() is None)

        app.earliest_expiry_date = date.today() - timedelta(days=1)
        app.save()
        self.assertEqual(app.get_num_days_since_expiration(), 1)


    def test_get_num_days_until_expiration(self):
        app = ApplicationFactory()
        self.assertTrue(app.get_num_days_until_expiration() is None)

        app.earliest_expiry_date = date.today()
        app.save()
        self.assertTrue(app.get_num_days_until_expiration() is None)

        app.earliest_expiry_date = date.today() + timedelta(days=1)
        app.save()
        self.assertTrue(app.get_num_days_until_expiration() is 1)

        app.earliest_expiry_date = date.today() - timedelta(days=1)
        app.save()
        self.assertTrue(app.get_num_days_until_expiration() is None)


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
        app_pending = ApplicationFactory(status=Application.PENDING,
            partner=partner)
        self.assertFalse(app_pending.is_renewable)

        app_question = ApplicationFactory(status=Application.QUESTION,
            partner=partner)
        self.assertFalse(app_question.is_renewable)

        app_not_approved = ApplicationFactory(status=Application.NOT_APPROVED,
            partner=partner)
        self.assertFalse(app_not_approved.is_renewable)

        # Applications whose partners don't have renewals_available cannot be
        # renewed.
        partner2 = PartnerFactory(renewals_available=False)
        app = ApplicationFactory(partner=partner2, status=Application.APPROVED)
        self.assertFalse(app.is_renewable)

        # Other applications can be renewed!
        good_app = ApplicationFactory(partner=partner,
            status=Application.APPROVED)
        self.assertTrue(good_app.is_renewable)

        good_app2 = ApplicationFactory(partner=partner,
            status=Application.SENT)
        self.assertTrue(good_app.is_renewable)

        delete_me = [app1, app2, app_pending, app_question, app_not_approved,
                     app, good_app, good_app2]

        for app in delete_me:
            app.delete()


    def test_renew_good_app(self):
        stream = StreamFactory()
        editor = EditorFactory()
        editor2 = EditorFactory()
        partner = PartnerFactory(renewals_available=True)
        app = ApplicationFactory(
                rationale='Because I said so',
                specific_title='The one with the blue cover',
                specific_stream=stream,
                comments='No comment',
                agreement_with_terms_of_use=True,
                editor=editor,
                partner=partner,
                status=Application.APPROVED,
                date_closed=date.today() + timedelta(days=1),
                days_open=1,
                earliest_expiry_date=date.today() + timedelta(days=366),
                sent_by=editor2.user
              )

        app2 = app.renew()

        # Just checking.
        self.assertTrue(isinstance(app2, Application))

        # Fields that should be copied, were.
        self.assertEqual(app2.rationale, 'Because I said so')
        self.assertEqual(app2.specific_title, 'The one with the blue cover')
        self.assertEqual(app2.specific_stream, stream)
        self.assertEqual(app2.comments, 'No comment')
        self.assertEqual(app2.agreement_with_terms_of_use, True)
        self.assertEqual(app2.editor, editor)
        self.assertEqual(app2.partner, partner)

        # Fields that should be cleared or reset, were.
        self.assertEqual(app2.status, Application.PENDING)
        self.assertFalse(app2.date_closed)
        self.assertFalse(app2.days_open)
        self.assertFalse(app2.earliest_expiry_date)
        self.assertFalse(app2.sent_by)
        self.assertEqual(app2.parent, app)


    def test_renew_bad_app(self):
        partner = PartnerFactory(renewals_available=False)
        app = ApplicationFactory(partner=partner)
        self.assertFalse(app.renew())


    def test_is_expiring_soon_1(self):
        """
        Returns False if the app has already expired.
        """
        app = ApplicationFactory(
            earliest_expiry_date=date.today() - timedelta(days=1))
        self.assertFalse(app.is_expiring_soon())


    def test_is_expiring_soon_2(self):
        """
        Returns False if the app expired today.
        """
        app = ApplicationFactory(
            earliest_expiry_date=date.today())
        self.assertFalse(app.is_expiring_soon())


    def test_is_expiring_soon_3(self):
        """
        Returns True if the app expires tomorrow.
        """
        app = ApplicationFactory(
            earliest_expiry_date=date.today() + timedelta(days=1))
        self.assertTrue(app.is_expiring_soon())


    def test_is_expiring_soon_4(self):
        """
        Returns True if the app expires in 30 days.
        """
        app = ApplicationFactory(
            earliest_expiry_date=date.today() + timedelta(days=30))
        self.assertTrue(app.is_expiring_soon())


    def test_is_expiring_soon_5(self):
        """
        Returns False if the app expires in 31 days.
        """
        app = ApplicationFactory(
            earliest_expiry_date=date.today() + timedelta(days=31))
        self.assertFalse(app.is_expiring_soon())



class EvaluateApplicationTest(TestCase):
    def setUp(self):
        super(EvaluateApplicationTest, self).setUp()
        editor = EditorFactory()
        self.user = editor.user

        coordinators = get_coordinators()
        coordinators.user_set.add(self.user)

        self.partner = PartnerFactory()

        self.application = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=self.partner,
            rationale='Just because',
            agreement_with_terms_of_use=True)
        self.url = reverse('applications:evaluate',
            kwargs={'pk': self.application.pk})

        editor2 = EditorFactory()
        self.unpriv_user = editor2.user

        self.message_patcher = patch('TWLight.applications.views.messages.add_message')
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

        # Approve the application
        response = self.client.post(self.url,
            data={'status': Application.APPROVED},
            follow=True)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.APPROVED)


    def test_sets_days_open(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Approve the application
        response = self.client.post(self.url,
            data={'status': Application.APPROVED},
            follow=True)

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
        response = self.client.post(self.url,
            data={'status': Application.APPROVED},
            follow=True)

        # Verify date closed
        self.application.refresh_from_db()
        self.assertEqual(self.application.date_closed, date.today())



class BatchEditTest(TestCase):
    def setUp(self):
        super(BatchEditTest, self).setUp()
        self.url = reverse('applications:batch_edit')
        editor = EditorFactory()
        self.user = editor.user

        coordinators = get_coordinators()
        coordinators.user_set.add(self.user)

        self.partner = PartnerFactory()

        self.application = ApplicationFactory(
            editor=editor,
            status=Application.PENDING,
            partner=self.partner,
            rationale='Just because',
            agreement_with_terms_of_use=True)

        editor2 = EditorFactory()
        self.unpriv_user = editor2.user

        self.message_patcher = patch('TWLight.applications.views.messages.add_message')
        self.message_patcher.start()


    def tearDown(self):
        super(BatchEditTest, self).tearDown()
        self.message_patcher.stop()


    def test_missing_params_raise_http_bad_request(self):
        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        # No post data: bad.
        response = self.client.post(self.url, data={}, follow=True)
        self.assertEqual(response.status_code, 400)

        # Missing the 'applications' parameter: bad.
        response = self.client.post(self.url, data={'batch_status': 1}, follow=True)
        self.assertEqual(response.status_code, 400)

        # Missing the 'batch_status' parameter: bad.
        response = self.client.post(self.url, data={'applications': 1}, follow=True)
        self.assertEqual(response.status_code, 400)

        # Has both parameters, but 'batch_status' has an invalid value: bad.

        assert 6 not in [Application.PENDING,
                         Application.QUESTION,
                         Application.APPROVED,
                         Application.NOT_APPROVED]

        response = self.client.post(self.url,
            data={'applications': 1, 'batch_status': 6}, follow=True)
        self.assertEqual(response.status_code, 400)


    def test_bogus_applications_parameter_handled(self):
        """
        If the applications parameter doesn't correspond to an existing
        application, the http request should succeed, but no apps should be
        changed.
        """

        # Check status quo ante.
        self.assertEqual(Application.objects.count(), 1)

        # Make sure that the batch_status value does *not* fail the request - we
        # want to be clear that we're testing the applications parameter.
        assert 3 in [Application.PENDING,
                     Application.QUESTION,
                     Application.APPROVED,
                     Application.NOT_APPROVED]

        # Make sure the applications parameter actually is bogus.
        assert Application.objects.filter(pk=2).count() == 0

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        # Issue the request. Don't follow redirects from here.
        response = self.client.post(self.url,
            data={'applications': 2, 'batch_status': 3}, follow=False)

        # Check things! We get redirected to the applications page when done.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path,
            reverse('applications:list'))

        # No new apps created
        self.assertEqual(Application.objects.count(), 1)

        # Refresh object from db to check for changes (there shouldn't be any).
        app = Application.objects.get(pk=self.application.pk)

        self.assertEqual(app.editor, self.user.editor)
        self.assertEqual(app.partner, self.partner)
        self.assertEqual(app.status, Application.PENDING)
        self.assertEqual(app.rationale, 'Just because')
        self.assertEqual(app.agreement_with_terms_of_use, True)


    def test_only_coordinators_can_batch_edit(self):
        # An anonymous user is prompted to login.
        response = self.client.post(self.url,
            data={'applications': self.application.pk, 'batch_status': 3},
            folllow=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path,
            settings.LOGIN_URL)

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=False)

        # A user who is not a coordinator does not have access.
        coordinators = get_coordinators()
        coordinators.user_set.remove(editor) # make sure
        response = self.client.post(self.url,
            data={'applications': self.application.pk, 'batch_status': 3},
            folllow=False)

        self.assertEqual(response.status_code, 403)

        # A coordinator may post to the page (on success, it redirects to the
        # application list page which they likely started on).
        request.user = self.user
        coordinators.user_set.add(self.user) # make sure
        response = views.BatchEditView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path,
            reverse('applications:list'))


    def test_sets_status(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.save()

        request = factory.post(self.url,
            data={'applications': self.application.pk,
                  'batch_status': Application.APPROVED})

        request.user = self.user
        coordinators = get_coordinators()
        coordinators.user_set.add(self.user) # make sure
        _ = views.BatchEditView.as_view()(request)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.APPROVED)


    def test_sets_days_open(self):
        factory = RequestFactory()

        self.application.status = Application.PENDING
        self.application.date_created = date.today() - timedelta(days=3)
        self.application.save()

        # Create an coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Approve the application
        response = self.client.post(self.url,
            data={'applications': self.application.pk,
                  'batch_status': Application.APPROVED},
            follow=True)

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
        response = self.client.post(self.url,
            data={'applications': self.application.pk,
                  'batch_status': Application.APPROVED},
            follow=True)

        # Verify date closed
        self.application.refresh_from_db()
        self.assertEqual(self.application.date_closed, date.today())

# posting to batch edit without app or status fails appropriately?


class MarkSentTest(TestCase):
    def setUp(self):
        super(MarkSentTest, self).setUp()
        editor = EditorFactory()
        self.user = editor.user

        coordinators = get_coordinators()
        coordinators.user_set.add(self.user)

        self.partner = PartnerFactory()
        self.partner2 = PartnerFactory()

        self.app1 = ApplicationFactory(
            editor=editor,
            status=Application.APPROVED,
            partner=self.partner,
            rationale='Just because',
            agreement_with_terms_of_use=True)

        self.app2 = ApplicationFactory(
            editor=editor,
            status=Application.APPROVED,
            partner=self.partner2,
            rationale='Just because',
            agreement_with_terms_of_use=True)

        editor2 = EditorFactory()
        self.unpriv_user = editor2.user

        self.url = reverse('applications:send_partner',
            kwargs={'pk': self.partner.pk})

        self.message_patcher = patch('TWLight.applications.views.messages.add_message')
        self.message_patcher.start()


    def tearDown(self):
        super(MarkSentTest, self).tearDown()
        self.message_patcher.stop()


    def test_invalid_params_raise_http_bad_request(self):
        # No post data: bad.
        request = RequestFactory().post(self.url, data={})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk)
        self.assertEqual(response.status_code, 400)

        # Missing the 'applications' parameter: bad.
        request = RequestFactory().post(self.url, data={'bogus': 1})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk)
        self.assertEqual(response.status_code, 400)


    def test_bogus_applications_parameter_handled(self):
        """
        If the applications parameter doesn't correspond to an existing
        application, the http request should succeed, but no apps should be
        changed.
        """
        # Check status quo ante.
        self.assertEqual(Application.objects.count(), 2)
        self.assertEqual(Application.objects.filter(
            status=Application.APPROVED).count(), 2)

        # Post a completely invalid app pk.
        request = RequestFactory().post(self.url,
            data={'applications': ['NaN']})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk)
        self.assertEqual(response.status_code, 400)

        self.app1.refresh_from_db()
        self.app2.refresh_from_db()
        self.assertEqual(self.app1.status, Application.APPROVED)
        self.assertEqual(self.app2.status, Application.APPROVED)

        # Post a valid app pk that doesn't correspond to the partner. That's
        # weird, but as long as we don't change anything's status it's fine.
        request = RequestFactory().post(self.url,
            data={'applications': [self.app2.pk]})
        request.user = self.user

        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

        self.app1.refresh_from_db()
        self.app2.refresh_from_db()
        self.assertEqual(self.app1.status, Application.APPROVED)
        self.assertEqual(self.app2.status, Application.APPROVED)

        # Check that we've covered all existing apps with the above statements.
        self.assertEqual(Application.objects.count(), 2)


    def test_only_coordinators_can_mark_sent(self):
        # An anonymous user is prompted to login.
        request = RequestFactory().post(self.url,
            data={'applications': [self.app2.pk]})
        request.user = AnonymousUser()

        with self.assertRaises(PermissionDenied):
            _ = views.SendReadyApplicationsView.as_view()(
                request, pk=self.partner.pk)

        # A user who is not a coordinator does not have access.
        coordinators = get_coordinators()
        coordinators.user_set.remove(self.unpriv_user) # make sure
        request.user = self.unpriv_user

        with self.assertRaises(PermissionDenied):
            _ = views.SendReadyApplicationsView.as_view()(
                request, pk=self.partner.pk)

        # A coordinator may post to the page.
        coordinators.user_set.add(self.user) # make sure
        request.user = self.user
        response = views.SendReadyApplicationsView.as_view()(
            request, pk=self.partner.pk)

        # Expected success condition: redirect back to the original page.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
