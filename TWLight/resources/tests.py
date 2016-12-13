from datetime import date, timedelta
from mock import patch

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import Http404
from django.test import TestCase, RequestFactory

from TWLight.applications import views as app_views
from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.users.factories import EditorFactory, UserProfileFactory
from TWLight.users.groups import get_coordinators

from .factories import PartnerFactory, StreamFactory
from .models import Language, RESOURCE_LANGUAGES, Partner
from .views import PartnersDetailView, PartnersListView

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
        cls.message_patcher.stop()


    def test_get_languages(self):
        partner = PartnerFactory()

        # At first, the list of languages should be empty.
        self.assertFalse(partner.languages.all())

        partner.languages.add(self.lang_en)
        self.assertEqual(partner.get_languages, u'English')

        # Order isn't important.
        partner.languages.add(self.lang_fr)
        self.assertIn(partner.get_languages,
            [u'English, French', u'French, English'])


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
        list_url = reverse('partners:list')

        editor = EditorFactory()

        request = RequestFactory().get(list_url)
        request.user = editor.user
        response = PartnersListView.as_view()(request)

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
        list_url = reverse('partners:list')

        editor = EditorFactory()
        editor.user.is_staff = True
        editor.user.save()

        request = RequestFactory().get(list_url)
        request.user = editor.user
        response = PartnersListView.as_view()(request)

        self.assertContains(response, partner.get_absolute_url())


    def test_review_app_page_excludes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.PENDING)

        url = reverse('applications:list')

        request = RequestFactory().get(url)
        request.user = self.coordinator
        response = app_views.ListApplicationsView.as_view()(request)

        self.assertNotContains(response, partner.company_name)


    def test_renew_app_page_excludes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)

        # This application expires soon.
        tomorrow = date.today() + timedelta(days=1)
        _ = ApplicationFactory(partner=partner,
            status=Application.SENT,
            earliest_expiry_date=tomorrow)
        url = reverse('applications:list_expiring')

        request = RequestFactory().get(url)
        request.user = self.coordinator
        response = app_views.ListExpiringApplicationsView.as_view()(request)

        self.assertNotContains(response, partner.company_name)


    def test_sent_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.SENT)
        url = reverse('applications:list_sent')

        request = RequestFactory().get(url)
        request.user = self.coordinator
        response = app_views.ListSentApplicationsView.as_view()(request)

        self.assertContains(response, partner.company_name)


    def test_rejected_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.NOT_APPROVED)
        url = reverse('applications:list_rejected')

        request = RequestFactory().get(url)
        request.user = self.coordinator
        response = app_views.ListRejectedApplicationsView.as_view()(request)

        self.assertContains(response, partner.company_name)


    def test_approved_app_page_includes_not_available(self):
        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        _ = ApplicationFactory(partner=partner, status=Application.APPROVED)
        url = reverse('applications:list_approved')

        request = RequestFactory().get(url)
        request.user = self.coordinator
        response = app_views.ListApprovedApplicationsView.as_view()(request)

        self.assertContains(response, partner.company_name)



class StreamModelTests(TestCase):

    @classmethod
    def setUpClass(cls):
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
            [u'English, French', u'French, English'])
