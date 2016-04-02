from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.fields import BooleanField
from django.test import TestCase, Client, RequestFactory

from TWLight.applications import views
from TWLight.resources.models import Partner
from TWLight.resources.factories import PartnerFactory
from TWLight.users.factories import EditorFactory

"""
totally test that resources.models.Partner, applications.models.Application,
and applications.helpers are in sync.
"""


class RequestApplicationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = reverse('applications:request')
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

        cls.coordinator = User.objects.create_user(
            username='coordinator', password='coordinator')


    @classmethod
    def tearDownClass(cls):
        cls.editor.delete()
        cls.editor2.delete()
        cls.coordinator.delete()


    def tearDown(self):
        for partner in Partner.objects.all():
            partner.delete()


    def _get_isolated_view(self):
        """
        Get an instance of the view that we can test in isolation, without
        requiring Client().
        """
        request = RequestFactory().get(self.url)
        view = views.RequestApplicationView()
        view.request = request
        return view


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
        self.client.login(username='editor', password='editor2')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


    def test_form_class(self):
        """
        Ensure that the form created by RequestApplicationView has one
        BooleanField per Partner in the database, to allow Editors to select
        the ones they wish to apply for.
        """
        view = self._get_isolated_view()

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
        self.client.login(username='editor', password='editor')
        response = self.client.post(self.url, data={}, follow=True)
        self.assertEqual(response.request['PATH_INFO'], self.url)
        self.assertEqual(self.client.session[views.PARTNERS_SESSION_KEY], [])


    def test_valid_form_redirects(self):
        """
        Users who submit a valid form end up on the application page.
        """
        p1 = PartnerFactory()
        p2 = PartnerFactory()

        self.client.login(username='editor', password='editor')
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

        self.client.login(username='editor', password='editor')
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

"""

# SubmitApplicationView
Authorization: Editors only
invalid session key redirects to RfA
missing session key redirects to RfA
constructed form has the fields we expect, in the numbers we expect (try with several partner combos)
form initial data matches user profile
on success, redirects to user home
on success, updates user profile
on success, creates Applications for each partner, which match the form data
can you test _get_partners directly?
and _get_partner_fields?
and _get_user_fields?

# ListApplicationsView
Authorization: Coordinators and superusers only
Shows pending and question, but not approved or unapproved partners (test queryset or template render?)

Similar tests for approved and rejected lists
"""

"""
Desired behavior...

Users go to a screen where they select the resources they would like to apply
for. This should be a form constructed on the fly from all resources in the
system. (Which means we need to set another flag for making them available or
not.)

Submitting this creates a _request for application_ - a list of entities they
want to apply for. I don't think we need to actually persist this data past the
session?

I think if I'm going to do this in a relatively transparent and maintainable
way, I'm going to end up hardcoding the same optional-field information in
several places. And if I'm going to do THAT, I need to test it. So test that the
following cover the same fields:
* some authoritative source of truth about optional fields
* the list of optional fields available on Resource
* the list of optional fields available in OptionalApplication

RfA may actually be a stub application - just boolean values on all the 
resources. But ugh, I actually want to generate that dynamically from available
resources. So no. I think on form valid, an RfA generates an Application which
I can then persist.

What about caching the RfA form so we don't need to make it every time? And
quite frankly the subforms only need to be regenerated when their FKed objects
change. Hm.

django-material relies too heavily on JS; noscript will break the UI. Wonder how
much I can harvest from them or google for forms without JS.

users need to be able to see their own application status
"""