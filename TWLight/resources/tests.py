# -*- coding: utf-8 -*-
from datetime import date, timedelta
from mock import patch

from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import Http404
from django.test import Client, TestCase, RequestFactory

from TWLight.applications import views as app_views
from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.applications.views import RequestApplicationView
from TWLight.users.factories import EditorFactory, UserProfileFactory
from TWLight.users.groups import get_coordinators

from .factories import PartnerFactory, StreamFactory
from .models import Language, RESOURCE_LANGUAGES, Partner
from .views import PartnersDetailView, PartnersFilterView, PartnersToggleWaitlistView
from .filters import PartnerFilter

def EditorCraftRoom(self, Terms=False, Coordinator=False):
    """
    The use of the @login_required decorator on many views precludes the use of
    factories for many tests. This method creates an Editor logged into a test
    client session.
    """
    terms_url = reverse('terms')

    # Create and editor and set a password
    editor = EditorFactory()
    editor.user.set_password('editor')
    editor.user.save()

    # Log user in
    self.client = Client()
    session = self.client.session
    self.client.login(username=editor.user.username, password='editor')

    # Agree to terms of use in Client (or not).
    if Terms:
        terms = self.client.get(terms_url, follow=True)
        terms_form = terms.context['form']
        data = terms_form.initial
        data['terms_of_use'] = True
        data['submit'] = True
        agree = self.client.post(terms_url, data)

    # Add or remove editor from Coordinators as required
    coordinators = get_coordinators()

    if Coordinator:
        coordinators.user_set.add(editor.user)
    else:
        coordinators.user_set.remove(editor.user)

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
        cls.lang_en, _ = Language.objects.get_or_create(language='en')
        cls.lang_fr, _ = Language.objects.get_or_create(language='fr')


    def test_validation(self):
        # Note that RESOURCE_LANGUAGES is a list of tuples, such as
        # `('en', 'English')`, but we only care about the first element of each
        # tuple, as it is the one stored in the database.
        language_codes = [lang[0] for lang in RESOURCE_LANGUAGES]

        not_a_language = 'fksdja'
        assert not_a_language not in language_codes
        bad_lang = Language(language=not_a_language)
        with self.assertRaises(ValidationError):
            bad_lang.save()


    def test_language_display(self):
        self.assertEqual(self.lang_en.__unicode__(), 'English')


    def test_language_uniqueness(self):
        with self.assertRaises(IntegrityError):
            lang = Language(language='en')
            lang.save()



class PartnerModelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super(PartnerModelTests, cls).setUpClass()
        cls.lang_en, _ = Language.objects.get_or_create(language='en')
        cls.lang_fr, _ = Language.objects.get_or_create(language='fr')

        editor = EditorFactory()
        coordinators = get_coordinators()
        coordinators.user_set.add(editor.user)
        UserProfileFactory(user=editor.user, terms_of_use=True)

        cls.coordinator = editor.user

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch('TWLight.applications.views.messages.add_message')
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
        self.assertEqual(list(partner.get_languages), [Language.objects.get(language='en')])

        partner.languages.add(self.lang_fr)
        self.assertIn(
            Language.objects.get(language='fr'),
            list(partner.get_languages)
        )


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
        filter_url = reverse('partners:filter')

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
        filter_url = reverse('partners:filter')

        editor = EditorFactory()
        editor.user.is_staff = True
        editor.user.save()

        request = RequestFactory().get(filter_url)
        request.user = editor.user
        response = PartnersFilterView.as_view(filterset_class=PartnerFilter)(request)

        self.assertContains(response, partner.get_absolute_url())


    def test_review_app_page_excludes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.PENDING)

        url = reverse('applications:list')

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Test response.
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, partner.company_name)


    def test_renew_app_page_excludes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)

        tomorrow = date.today() + timedelta(days=1)
        _ = ApplicationFactory(partner=partner,
            status=Application.SENT)
        url = reverse('applications:list_renewal')

        # Create a coordinator with a test client session
        editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        # Test response.
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, partner.company_name)


    def test_sent_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.SENT)
        url = reverse('applications:list_sent')

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
        self.assertNotContains(denyResponse, partner.company_name)

	# Applications should be visible to the designated coordinator
	self.assertContains(allowResponse, partner.company_name)


    def test_rejected_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.NOT_APPROVED)
        url = reverse('applications:list_rejected')

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
        self.assertNotContains(denyResponse, partner.company_name)

	# Applications should be visible to the designated coordinator
	self.assertContains(allowResponse, partner.company_name)


    def test_approved_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.APPROVED)
        url = reverse('applications:list_approved')

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
        self.assertNotContains(denyResponse, partner.company_name)

	# Applications should be visible to the designated coordinator
	self.assertContains(allowResponse, partner.company_name)

    def test_statuses_exist(self):
        """
        AVAILABLE, NOT_AVAILABLE, WAITLIST should be the status choices.
        """

        assert hasattr(Partner, 'AVAILABLE')
        assert hasattr(Partner, 'NOT_AVAILABLE')
        assert hasattr(Partner, 'WAITLIST')

        assert hasattr(Partner, 'STATUS_CHOICES')

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
        self.assertQuerysetEqual(Partner.objects.all(),
                                 map(repr, Partner.even_not_available.filter(
                                    status__in=
                                    [Partner.WAITLIST, Partner.AVAILABLE])))



class WaitlistBehaviorTests(TestCase):
    """
    Tests of user-visible behavior with respect to waitlist status. We're
    *not* testing particular HTML messages as those kinds of tests tend to be
    extremely brittle.
    """

    @classmethod
    def setUpClass(cls):
        super(WaitlistBehaviorTests, cls).setUpClass()
        cls.message_patcher = patch('TWLight.applications.views.messages.add_message')
        cls.message_patcher.start()

    def test_request_application_view_context_1(self):
        """
        The any_waitlisted context on RequestApplicationView should True if
        there are waitlisted Partners.
        """
        # Set up request.
        req_url = reverse('applications:request')

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        # Ensure there is at least one waitlisted partner.
        partner = PartnerFactory(status=Partner.WAITLIST)

        # Test response.
        response = self.client.get(req_url, follow=True)
        self.assertEqual(response.context['any_waitlisted'], True)


    def test_request_application_view_context_2(self):
        """
        The any_waitlisted context on RequestApplicationView should False if
        there are not waitlisted Partners.
        """
        # Set up request.
        req_url = reverse('applications:request')

        # Create an editor with a test client session
        editor = EditorCraftRoom(self, Terms=True)

        # Ensure there are no waitlisted partners.
        for partner in Partner.objects.filter(status=Partner.WAITLIST):
            partner.delete()

        # Test response.
        response = self.client.get(req_url, follow=True)
        self.assertEqual(response.context['any_waitlisted'], False)


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
        url = reverse('partners:toggle_waitlist', kwargs={'pk': partner.pk})

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
        url = reverse('partners:toggle_waitlist', kwargs={'pk': partner.pk})

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
        url = reverse('partners:toggle_waitlist', kwargs={'pk': partner.pk})

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
        cls.lang_en, _ = Language.objects.get_or_create(language='en')
        cls.lang_fr, _ = Language.objects.get_or_create(language='fr')


    def test_get_languages(self):
        stream = StreamFactory()

        # At first, the list of languages should be empty.
        self.assertFalse(stream.languages.all())

        stream.languages.add(self.lang_en)
        self.assertEqual(stream.get_languages, u'English')

        # Order isn't important.
        stream.languages.add(self.lang_fr)
        self.assertIn(stream.get_languages,
            [u'English, français', u'français, English'])
