# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.fields import BooleanField
from django.test import TestCase, Client, RequestFactory

from TWLight.resources.models import Partner, Stream
from TWLight.resources.factories import PartnerFactory
from TWLight.users.factories import EditorFactory
from TWLight.users.models import Editor

from . import views
from .helpers import USER_FORM_FIELDS
from .factories import ApplicationFactory
from .forms import BaseApplicationForm
from .models import Application
"""
totally test that resources.models.Partner, applications.models.Application,
and applications.helpers are in sync.
"""

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

    # TODO top-level docs with update instructions for future-us
    # TODO actually write this test
    """

    def test_user_form_fields_reflected_in_partner(self):
        for field in USER_FORM_FIELDS:
            self.assertTrue(hasattr(Partner, field))
            print Partner._meta.get_field(field)


class BaseApplicationViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(BaseApplicationTest, cls).setUpClass()
        cls.client = Client()

        # Note: not an Editor.
        cls.base_user = User.objects.create_user(
            username='base_user', password='base_user')

        cls.editor = User.objects.create_user(
            username='editor', password='editor')
        EditorFactory(user=cls.editor)

        cls.editor2 = User.objects.create_user(
            username='editor2', password='editor2')
        EditorFactory(user=cls.editor2)

        # TODO needs to actually be coordinator
        cls.coordinator = User.objects.create_user(
            username='coordinator', password='coordinator')


    @classmethod
    def tearDownClass(cls):
        super(BaseApplicationTest, cls).tearDownClass()
        cls.base_user.delete()
        cls.editor.delete()
        cls.editor2.delete()
        cls.coordinator.delete()


    def tearDown(self):
        super(BaseApplicationTest, self).tearDown()
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


    def _login_editor(self):
        self.client.login(username='editor', password='editor')



class RequestApplicationTest(BaseApplicationViewTest):
    @classmethod
    def setUpClass(cls):
        super(RequestApplicationTest, cls).setUpClass()
        cls.url = reverse('applications:request')


    def test_authorization(self):
        """
        Only Editors should be able to request access to applications.
        """
        # An anonymous user is prompted to login.
        response = self.client.get(self.url)

        self.assertRedirects(response, settings.LOGIN_URL)

        # A user who is not a WP editor does not have access.
        self.client.login(username='base_user', password='base_user')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

        # An editor may see the page.
        self._login_editor()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


    def test_form_class(self):
        """
        Ensure that the form created by RequestApplicationView has one
        BooleanField per Partner in the database, to allow Editors to select
        the ones they wish to apply for.
        """
        view = self._get_isolated_view(views.RequestApplicationView)

        # Check that it works with only one Partner in the database.
        partner = PartnerFactory()

        form_class = view.get_form_class()
        form = form_class()
        self.assertEqual(len(form.fields), 1)

        fieldkey = 'partner_{id}'.format(id=partner.id)
        self.assertIn(fieldkey, form.fields)
        assert isinstance(form.fields[fieldkey], BooleanField)

        # Add Partners and seee how many form fields there are. We'll assume
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
        self._login_editor()
        response = self.client.post(self.url, data={}, follow=True)
        self.assertEqual(response.request['PATH_INFO'], self.url)
        self.assertEqual(self.client.session[views.PARTNERS_SESSION_KEY], [])


    def test_valid_form_redirects(self):
        """
        Users who submit a valid form end up on the application page.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        self._login_editor()
        data = {
            'partner_{id}'.format(id=p1.id): True,
            'partner_{id}'.format(id=p2.id): False,
        }
        response = self.client.post(self.url, data=data, follow=True)
        self.assertEqual(response.request['PATH_INFO'], 
            reverse('applications:apply'))


    def test_valid_form_writes_session_key(self):
        """
        Users who submit a valid form generate a matching session key.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        self._login_editor()
        data = {
            'partner_{id}'.format(id=p1.id): True,
            'partner_{id}'.format(id=p2.id): False,
        }
        response = self.client.post(self.url, data=data, follow=True)
        self.assertEqual(self.client.session[views.PARTNERS_SESSION_KEY], [p1.id])

        data = {
            'partner_{id}'.format(id=p1.id): False,
            'partner_{id}'.format(id=p2.id): True,
        }
        response = self.client.post(self.url, data=data, follow=True)
        self.assertEqual(self.client.session[views.PARTNERS_SESSION_KEY], [p2.id])

        data = {
            'partner_{id}'.format(id=p1.id): True,
            'partner_{id}'.format(id=p2.id): True,
        }
        response = self.client.post(self.url, data=data, follow=True)

        # Since we don't care which order the IDs are in, but list comparison
        # is sensitive to order, let's check first that both lists have the
        # same elements, and second that they are of the same length.
        self.assertEqual(set(self.client.session[views.PARTNERS_SESSION_KEY]),
            set([p2.id, p1.id]))
        self.assertEqual(len(self.client.session[views.PARTNERS_SESSION_KEY]),
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
        Only Editors should be able to request access to applications.
        """
        # An anonymous user is prompted to login.
        response = self.client.get(self.url)

        self.assertRedirects(response, settings.LOGIN_URL)

        # A user who is not a WP editor does not have access.
        self.client.login(username='base_user', password='base_user')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

        # An editor may see the page.
        self._login_editor()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


    def test_missing_session_key(self):
        """
        If the PARTNERS_SESSION_KEY is missing, the view should redirect to
        RequestApplicationView.
        """
        self._login_editor()

        session = self.client.session
        if views.PARTNERS_SESSION_KEY in session.keys():
            del session[views.PARTNERS_SESSION_KEY]
            session.save()

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('applications:request'))


    def test_empty_session_key(self):
        """
        If the PARTNERS_SESSION_KEY is an empty list, the view should redirect
        to RequestApplicationView.
        """
        self._login_editor()

        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = []
        session.save()

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('applications:request'))


    def test_invalid_session_data(self):
        """
        If the PARTNERS_SESSION_KEY is not a list of valid pks of Partners, the
        view should redirect to RequestApplicationView.
        """
        _ = PartnerFactory()

        self._login_editor()

        # Invalid pk: not an integer
        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = ['cats']
        session.save()

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('applications:request'))

        # Invalid pk: no such Partner
        self.assertEqual(Partner.objects.filter(pk=4500).count(), 0)

        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = [1, 4500]
        session.save()

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('applications:request'))


    def test_valid_session_data(self):
        """
        If the PARTNERS_SESSION_KEY is list of valid pks of Partners, the view
        should return OK.
        """
        p1 = PartnerFactory()

        self._login_editor()

        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = [p1.id]
        session.save()

        response = self.client.get(self.url)
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

        user = User.objects.create_user(
            username='alice', password='alice')
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

        Testing get_success_url in isolation doesn't work here because the
        view doesn't know about the messages middleware; we need to bring the
        client into play to get enough apparatus for our add_message call in
        get_success_url to work.
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

        self._login_editor()

        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = [p1.id]
        session.save()

        data = {
            'real_name': 'Anonymous Coward',
            'partner_{id}_rationale'.format(id=p1.id): 'Whimsy',
            'partner_{id}_comments'.format(id=p1.id): 'None whatsoever',
        }

        response = self.client.post(self.url, data=data, follow=True)

        expected_url = reverse('users:editor_detail',
                                kwargs={'pk': self.editor.pk})
        self.assertRedirects(response, expected_url)


    def test_user_profile_updates_on_success(self):
        """
        When the form post includes user data, the user profile should update
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

        user = User.objects.create_user(
            username='local_user', password='local_user')
        EditorFactory(
            user=user,
            # All 3 of these fields will be required by PartnerFactory.
            real_name='',
            country_of_residence='Lithuania',
            occupation='Cat floofer',
        )

        self.client.login(username='local_user', password='local_user')

        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = [p1.id]
        session.save()

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

        _ = self.client.post(self.url, data=data, follow=True)

        # Force reload from database to see updated values. (In Django 1.8 this
        # can be replaced with user.editor.refresh_from_db().)
        editor = Editor.objects.get(pk=user.editor.pk)

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

        self._login_editor()

        session = self.client.session
        session[views.PARTNERS_SESSION_KEY] = [p1.id, p2.id]
        session.save()

        data = {
            'partner_{id}_rationale'.format(id=p1.id): 'Whimsy',
            'partner_{id}_comments'.format(id=p1.id): 'None whatsoever',
            'partner_{id}_specific_title'.format(id=p1.id): 'Open Access for n00bs',
            'partner_{id}_rationale'.format(id=p2.id): 'Saving the world',
            'partner_{id}_comments'.format(id=p2.id): '',
            'partner_{id}_specific_stream'.format(id=p2.id): s1.pk,
        }

        _ = self.client.post(self.url, data=data, follow=True)

        # If the application has not been created, these lines will raise
        # DoesNotExist.
        app1 = Application.objects.get(partner=p1, user=self.editor)
        app2 = Application.objects.get(partner=p2, user=self.editor)

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
        ApplicationFactory(status=Application.APPROVED)
        ApplicationFactory(status=Application.APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)
        ApplicationFactory(status=Application.NOT_APPROVED)


    @classmethod
    def tearDownClass(cls):
        super(ListApplicationsTest, cls).tearDownClass()
        cls.superuser.delete()
        for app in Application.objects.all():
            app.delete()


    def _base_test_authorization(self, url):
        """
        Only Coordinators and superusers should be able to see application
        lists.
        """
        # An anonymous user is prompted to login.
        response = self.client.get(url)

        self.assertRedirects(response, settings.LOGIN_URL)

        # An editor who is not a coordinator may not see the page.
        self._login_editor()
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

        # A coordinator may see the page.
        self.client.login(username='coordinator', password='coordinator')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # A superuser may see the page.
        self.client.login(username='super', password='super')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)


    def _base_test_object_visibility(self, url, queryset):
        self.client.login(username='coordinator', password='coordinator')
        response = self.client.get(url)

        for obj in queryset:
            self.assertIn(obj.__str__(), response.content)


    def test_list_authorization(self):
        url = reverse('applications:list')
        self._base_test_authorization(url)


    def test_list_object_visibility(self):
        url = reverse('applications:list')
        queryset = Application.objects.filter(
            status__in=[Application.PENDING, Application.QUESTION])
        self._base_test_object_visibility(url, queryset)


    def test_list_approved_authorization(self):
        url = reverse('applications:list_approved')
        self._base_test_authorization(url)


    def test_list_approved_object_visibility(self):
        url = reverse('applications:list_approved')
        queryset = Application.objects.filter(
            status=Application.APPROVED)
        self._base_test_object_visibility(url, queryset)


    def test_list_rejected_authorization(self):
        url = reverse('applications:list_rejected')
        self._base_test_authorization(url)


    def test_list_rejected_object_visibility(self):
        url = reverse('applications:list_rejected')
        queryset = Application.objects.filter(
            status=Application.NOT_APPROVED)
        self._base_test_object_visibility(url, queryset)


"""
I think if I'm going to do this in a relatively transparent and maintainable
way, I'm going to end up hardcoding the same optional-field information in
several places. And if I'm going to do THAT, I need to test it. So test that the
following cover the same fields:
* some authoritative source of truth about optional fields
* the list of optional fields available on Resource
* the list of optional fields available in OptionalApplication

users need to be able to see their own application status
"""