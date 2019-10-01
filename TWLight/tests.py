from mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory, Client

from rest_framework.test import APIRequestFactory, force_authenticate

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.tests import EditorCraftRoom
from TWLight.resources.factories import PartnerFactory
from TWLight.resources.models import AccessCode, Partner
from TWLight.users.factories import UserFactory, EditorFactory
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Authorization, UserProfile, Editor
import TWLight.users.views

from . import views

from .view_mixins import (CoordinatorOrSelf,
                          CoordinatorsOnly,
                          EditorsOnly,
                          SelfOnly,
                          ToURequired,
                          EmailRequired)


coordinators = get_coordinators()


class ObjGet(object):
    """
    Some view mixins assume that the thing they're mixed with will define
    self.get_object. Therefore we provide a class that does only that, and which
    we can initialize to return whatever we need for the test.
    """
    def __init__(self, obj=None, *args, **kwargs):
        self.object = obj
        super(ObjGet, self).__init__(*args, **kwargs)


    def get_object(self):
        return self.object



class DispatchProvider(object):
    """
    All mixins assume the thing they're mixed with provides dispatch().
    It doesn't need to do anything, since we're testing whether the mixin
    raises PermissionDenied - it just needs to exist.
    """
    def dispatch(self, request, *args, **kwargs):
        return True



class TestCoordinatorOrSelf(CoordinatorOrSelf, ObjGet, DispatchProvider):
    pass



class TestCoordinatorsOnly(CoordinatorsOnly, DispatchProvider):
    pass



class TestEditorsOnly(EditorsOnly, DispatchProvider):
    pass



class TestSelfOnly(SelfOnly, ObjGet, DispatchProvider):
    pass



class TestToURequired(ToURequired, DispatchProvider):
    pass



class TestEmailRequired(EmailRequired, DispatchProvider):
    pass



class ViewMixinTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(ViewMixinTests, cls).setUpClass()
        # Some mixins add messages; don't make the tests fail simply because
        # MessageMiddleware is unavailable.
        cls.message_patcher = patch('TWLight.applications.views.messages.add_message')
        cls.message_patcher.start()


    @classmethod
    def tearDownClass(cls):
        super(ViewMixinTests, cls).tearDownClass()
        cls.message_patcher.stop()


    def tearDown(self):
        for user in User.objects.all():
            user.delete()


    def test_coordinators_or_self_1(self):
        """
        CoordinatorOrSelf should allow coordinators.
        """
        user = UserFactory()
        coordinators.user_set.add(user)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorOrSelf()

        # Should not raise error.
        #test.dispatch(req)
        pass


    def test_coordinators_or_self_2(self):
        """
        CoordinatorOrSelf should allow superusers.
        """
        user = UserFactory(is_superuser=True)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorOrSelf()

        test.dispatch(req)


    def test_coordinators_or_self_3(self):
        """
        CoordinatorOrSelf should users who are the same as the view's user,
        if view.get_object returns a user.
        """
        user = UserFactory()

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorOrSelf(obj=user)

        test.dispatch(req)


    def test_coordinators_or_self_4(self):
        """
        CoordinatorOrSelf should users who own the object returned by the
        view's get_object.
        """
        user = UserFactory()
        editor = EditorFactory(user=user)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorOrSelf(obj=editor)

        test.dispatch(req)


    def test_coordinators_or_self_5(self):
        """
        CoordinatorOrSelf should not allow users who fail all of the above
        criteria.
        """
        user = UserFactory(is_superuser=False)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorOrSelf(obj=None)

        with self.assertRaises(PermissionDenied):
            test.dispatch(req)


    def test_coordinators_only_1(self):
        """
        CoordinatorsOnly should allow coordinators.
        """
        user = UserFactory()
        coordinators.user_set.add(user)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorsOnly()

        test.dispatch(req)


    def test_coordinators_only_2(self):
        """
        CoordinatorsOnly should allow superusers.
        """
        user = UserFactory(is_superuser=True)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorsOnly()

        test.dispatch(req)


    def test_coordinators_only_3(self):
        """
        CoordinatorsOnly should disallow anyone not fitting the above two
        criteria.
        """
        user = UserFactory(is_superuser=False)

        req = RequestFactory()
        req.user = user

        test = TestCoordinatorsOnly()

        with self.assertRaises(PermissionDenied):
            test.dispatch(req)


    def test_editors_only_1(self):
        """
        EditorsOnly allows editors.
        """
        user = UserFactory()
        _ = EditorFactory(user=user)

        req = RequestFactory()
        req.user = user

        test = TestEditorsOnly()
        test.dispatch(req)


    def test_editors_only_2(self):
        """
        EditorsOnly does *not* allow superusers who aren't editors.
        """
        user = UserFactory(is_superuser=True)
        self.assertFalse(hasattr(user, 'editor'))

        req = RequestFactory()
        req.user = user

        test = TestEditorsOnly()
        with self.assertRaises(PermissionDenied):
            test.dispatch(req)


    def test_editors_only_3(self):
        """
        EditorsOnly does not allow non-superusers who aren't editors.
        """
        user = UserFactory(is_superuser=False)
        self.assertFalse(hasattr(user, 'editor'))

        req = RequestFactory()
        req.user = user

        test = TestEditorsOnly()
        with self.assertRaises(PermissionDenied):
            test.dispatch(req)


    def test_self_only_1(self):
        """
        SelfOnly allows users who are also the object returned by get_object.
        """
        user = UserFactory()

        req = RequestFactory()
        req.user = user

        test = TestSelfOnly(obj=user)

        test.dispatch(req)


    def test_self_only_2(self):
        """
        SelfOnly allows users who own the object returned by get_object.
        """
        user = UserFactory()
        editor = EditorFactory(user=user)

        req = RequestFactory()
        req.user = user

        test = TestSelfOnly(obj=editor)

        test.dispatch(req)


    def test_self_only_3(self):
        """
        SelfOnly disallows users who fail the above criteria.
        """
        # We'll need to force the usernames to be different so that the
        # underlying objects will end up different, apparently.
        user = UserFactory(username='alice')

        req = RequestFactory()
        req.user = user

        test = TestSelfOnly(obj=None)

        with self.assertRaises(PermissionDenied):
            test.dispatch(req)

        user2 = UserFactory(username='bob')
        test = TestSelfOnly(obj=user2)

        with self.assertRaises(PermissionDenied):
            test.dispatch(req)


    def test_tou_required_1(self):
        """
        ToURequired allows users who have agreed with the terms of use.
        """
        user = UserFactory()
        # The user profile should be created by signal on user creation.
        user.userprofile.terms_of_use = True
        user.userprofile.save()

        req = RequestFactory()
        req.user = user
        # ToURequired expects the request to have a path that it will use to
        # construct a next parameter. Doesn't matter what it is, but it needs
        # to exist.
        req.path = '/'

        test = TestToURequired()

        test.dispatch(req)


    def test_tou_required_2(self):
        """
        ToURequired allows superusers.
        """
        user = UserFactory(is_superuser=True)

        req = RequestFactory()
        req.user = user
        req.path = '/'

        test = TestToURequired()

        test.dispatch(req)


    def test_tou_required_3(self):
        """
        ToURequired disallows users who have failed the above criteria.
        """
        user = UserFactory(is_superuser=False)
        user.userprofile.terms_of_use = False
        user.userprofile.save()

        req = RequestFactory()
        req.user = user
        req.path = '/'

        test = TestToURequired()

        resp = test.dispatch(req)
        # This test doesn't deny permission; it asks people to agree with the
        # terms of use.
        self.assertTrue(isinstance(resp, HttpResponseRedirect))



    def test_email_required_1(self):
        """
        EmailRequired allows users who have an email on file.
        """
        user = UserFactory(email='definitely@has.email.com')

        req = RequestFactory()
        req.user = user
        # EmailRequired expects the request to have a path that it will use to
        # construct a next parameter. Doesn't matter what it is, but it needs
        # to exist.
        req.path = '/'

        test = TestEmailRequired()

        test.dispatch(req)


    def test_email_required_2(self):
        """
        EmailRequired allows superusers (even without email)
        """
        user = UserFactory(email='', is_superuser=True)

        req = RequestFactory()
        req.user = user
        req.path = '/'

        test = TestEmailRequired()

        test.dispatch(req)


    def test_email_required_2(self):
        """
        EmailRequired disallows users who fail the above criteria.
        """
        user = UserFactory(email='', is_superuser=False)

        req = RequestFactory()
        req.user = user
        req.path = '/'

        test = TestEmailRequired()

        resp = test.dispatch(req)
        # This test doesn't deny permission; it asks people to add their email.
        self.assertTrue(isinstance(resp, HttpResponseRedirect))



class ExampleApplicationsDataTest(TestCase):
    """
    As above, but for the example applications data script.
    """
    def test_command_output(self):
        # Needs a superuser first.
        user = UserFactory()

        call_command('user_example_data', '200')
        call_command('resources_example_data', '50')
        call_command('applications_example_data', '300')

class UserRenewalNoticeTest(TestCase):
    """
    Test the user renewal notice management command
    """
    def test_command_output(self):
        call_command('user_renewal_notice')



class AuthorizationBaseTestCase(TestCase):
    """
    Setup class for Authorization Object tests.
    Could possibly achieve the same effect via a new factory class.
    """
    def setUp(self):
        super(AuthorizationBaseTestCase, self).setUp()


        self.partner1 = PartnerFactory(
            authorization_method=Partner.EMAIL,
            status=Partner.AVAILABLE
        )
        self.partner2 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE
        )

        self.editor1 = EditorFactory()
        self.editor2 = EditorFactory()
        self.editor3 = EditorFactory()
        # Editor 4 is a coordinator with a session.
        self.editor4 = EditorCraftRoom(self, Terms=True, Coordinator=True)
        # Editor 4 is the designated coordinator for partners 1 and 2.
        self.partner1.coordinator = self.editor4.user
        self.partner1.save()
        self.partner2.coordinator = self.editor4.user
        self.partner2.save()

        # Create applications.
        self.app1 = ApplicationFactory(
            editor=self.editor1,
            partner=self.partner1,
            status = Application.PENDING,
            date_closed = None
        )
        self.app2 = ApplicationFactory(
            editor=self.editor2,
            partner=self.partner1,
            status = Application.PENDING,
            date_closed = None
        )
        self.app3 = ApplicationFactory(
            editor=self.editor3,
            partner=self.partner1,
            status = Application.PENDING,
            date_closed = None
        )
        self.app4 = ApplicationFactory(
            editor=self.editor1,
            partner=self.partner2,
            status = Application.PENDING,
            date_closed = None
        )
        self.app5 = ApplicationFactory(
            editor=self.editor2,
            partner=self.partner2,
            status = Application.PENDING,
            date_closed = None
        )
        self.app6 = ApplicationFactory(
            editor=self.editor3,
            partner=self.partner2,
            status=Application.PENDING,
            date_closed = None
        )

        # Editor 4 will update status on applications to partners 1 and 2.
        # Send the application
        self.client.post(
            reverse('applications:evaluate', kwargs={'pk': self.app1.pk}),
            data={'status': Application.SENT},
            follow=True
        )
        self.app1.refresh_from_db()
        self.auth_app1 = Authorization.objects.get(authorizer=self.editor4.user, authorized_user=self.editor1.user, partner=self.partner1)

        # Approve the application
        self.client.post(
            reverse('applications:evaluate', kwargs={'pk': self.app2.pk}),
            data={'status': Application.APPROVED},
            follow=True
        )
        self.app2.refresh_from_db()
        self.auth_app2 =  Authorization(authorizer=self.editor4.user, authorized_user=self.editor2.user, partner=self.partner1)

        # Send the application
        self.client.post(
            reverse('applications:evaluate', kwargs={'pk': self.app3.pk}),
            data={'status': Application.SENT},
            follow=True
        )
        self.app3.refresh_from_db()
        self.auth_app3 = Authorization.objects.get(authorizer=self.editor4.user, authorized_user=self.editor3.user, partner=self.partner1)

        # Send the application
        self.client.post(
            reverse('applications:evaluate', kwargs={'pk': self.app4.pk}),
            data={'status': Application.SENT},
            follow=True
        )
        self.app4.refresh_from_db()
        self.auth_app4 = Authorization.objects.get(authorizer=self.editor4.user, authorized_user=self.editor1.user, partner=self.partner2)

        # Send the application
        self.client.post(
            reverse('applications:evaluate', kwargs={'pk': self.app5.pk}),
            data={'status': Application.SENT},
            follow=True
        )
        self.app5.refresh_from_db()
        self.auth_app5 = Authorization.objects.get(authorizer=self.editor4.user, authorized_user=self.editor2.user, partner=self.partner2)



    def tearDown(self):
        super(AuthorizationBaseTestCase, self).tearDown()
        self.partner1.delete()
        self.partner2.delete()
        self.editor1.delete()
        self.editor2.delete()
        self.editor3.delete()
        self.editor4.delete()
        self.app1.delete()
        self.app2.delete()
        self.app3.delete()
        self.app4.delete()
        self.app5.delete()



class AuthorizationTestCase(AuthorizationBaseTestCase):
    """
    Tests that Authorizations are correctly created and updated based on user activity.
    """
    def test_approval_sets_authorizer(self):
        """
        Test that authorizer is correctly set.
        """
        self.assertEqual(self.auth_app1.authorizer, self.editor4.user)
        self.assertEqual(self.auth_app2.authorizer, self.editor4.user)
        self.assertEqual(self.auth_app3.authorizer, self.editor4.user)
        self.assertEqual(self.auth_app4.authorizer, self.editor4.user)
        self.assertEqual(self.auth_app5.authorizer, self.editor4.user)



class AuthorizedUsersAPITestCase(AuthorizationBaseTestCase):
    """
    Tests for the AuthorizedUsers view and API.
    """

    def test_authorized_users_api_denied(self):
        """
        Test that, if no credentials are supplied, the API returns no data.
        """
        factory = APIRequestFactory()
        request = factory.get('/api/v0/users/authorizations/partner/1')

        response = TWLight.users.views.AuthorizedUsers.as_view()(request, self.partner1.pk, 0)

        self.assertEqual(response.status_code, 401)

    def test_authorized_users_api_success(self):
        """
        Test that, if credentials are supplied, the API returns a 200 status code.
        """
        factory = APIRequestFactory()
        request = factory.get('/api/v0/users/authorizations/partner/1')
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(request, self.partner1.pk, 0)

        self.assertEqual(response.status_code, 200)

    def test_authorized_users_api_applications(self):
        """
        In the case of a non-proxy partner, we should return all users with
        a sent application.
        """
        factory = APIRequestFactory()
        request = factory.get('/api/v0/users/authorizations/partner/1')
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(request, self.partner1.pk, 0)

        expected_json = [{"wp_username": self.editor1.user.editor.wp_username},
                         {"wp_username": self.editor3.user.editor.wp_username}]

        self.assertEqual(response.data, expected_json)

    def test_authorized_users_api_authorizations(self):
        """
        In the case of a proxy partner, we should return all active authorizations
        for that partner.
        """
        factory = APIRequestFactory()
        request = factory.get('/api/v0/users/authorizations/partner/1')
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(request, self.partner2.pk, 0)

        expected_json = [{"wp_username": self.editor1.user.editor.wp_username},
                         {"wp_username": self.editor2.user.editor.wp_username}]

        self.assertEqual(response.data, expected_json)
