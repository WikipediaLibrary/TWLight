import csv
from mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory, Client

from TWLight.resources.factories import PartnerFactory
from TWLight.resources.models import AccessCode, Partner
from TWLight.users.factories import UserFactory, EditorFactory
from TWLight.users.groups import get_coordinators

from . import views

from .view_mixins import (CoordinatorOrSelf,
                          CoordinatorsOnly,
                          StaffOnly,
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



class TestStaffOnly(StaffOnly, DispatchProvider):
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


    def test_staff_only_1(self):
        user = UserFactory(is_staff=True)

        req = RequestFactory()
        req.user = user

        test = TestStaffOnly()

        test.dispatch(req)


    def test_staff_only_2(self):
        user = UserFactory(is_staff=False)

        req = RequestFactory()
        req.user = user

        test = TestStaffOnly()

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



class StaffDashboardTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(StaffDashboardTest, cls).setUpClass()

        cls.staff_user = UserFactory(username='staff_user', is_staff=True)
        cls.staff_user.set_password('staff')
        cls.staff_user.save()
        cls.user = UserFactory()

        cls.partner1 = PartnerFactory()
        cls.partner1_pk = cls.partner1.pk
        cls.partner2 = PartnerFactory()
        cls.partner2_pk = cls.partner2.pk
        cls.partner3 = PartnerFactory()
        cls.partner3_pk = cls.partner3.pk

        cls.url = reverse('staff')

        # We should mock out any call to messages call in the view, since
        # RequestFactory (unlike Client) doesn't run middleware. If you
        # actually want to test that messages are displayed, use Client(),
        # and stop/restart the patcher.
        cls.message_patcher = patch('TWLight.applications.views.messages.add_message')
        cls.message_patcher.start()


    @classmethod
    def tearDownClass(cls):
        super(StaffDashboardTest, cls).tearDownClass()
        cls.staff_user.delete()
        cls.user.delete()

        # If any access code objects have been created, delete them
        #access_codes = AccessCode.objects.all()
        #access_codes.delete()

        cls.message_patcher.stop()


    def test_staff_dashboard_staff(self):
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            _ = views.StaffDashboardView.as_view()(request)


    def test_staff_dashboard_non_staff(self):
        factory = RequestFactory()

        request = factory.get(self.url)
        request.user = self.staff_user

        response = views.StaffDashboardView.as_view()(request)
        self.assertEqual(response.status_code, 200)


    def test_staff_dashboard_upload(self):
        """
        A csv file with unique codes for multiple partners should
        upload successfully and create the relevant objects.
        """
        test_file = open('accesscodes.csv', 'wb')
        csv_writer = csv.writer(test_file, lineterminator='\n')
        csv_writer.writerow(('ABCD-EFGH-IJKL', str(self.partner1_pk)))
        csv_writer.writerow(('BBCD-EFGH-IJKL', str(self.partner1_pk)))
        csv_writer.writerow(('CBCD-EFGH-IJKL', str(self.partner2_pk)))
        test_file.close()

        client = Client()
        session = client.session
        client.login(username=self.staff_user.username, password='staff')

        with open('accesscodes.csv', 'r') as csv_file:
            response = client.post(self.url, {'access_code_csv': csv_file})

        access_codes = AccessCode.objects.all()
        self.assertEqual(access_codes.count(), 3)


    def test_staff_dashboard_duplicate(self):
        """
        A csv file with non-unique codes for multiple partners should
        only upload the unique ones.
        """
        test_file = open('accesscodes.csv', 'wb')
        csv_writer = csv.writer(test_file, lineterminator='\n')
        csv_writer.writerow(('ABCD-EFGH-IJKL', str(self.partner1_pk)))
        csv_writer.writerow(('BBCD-EFGH-IJKL', str(self.partner1_pk)))
        csv_writer.writerow(('ABCD-EFGH-IJKL', str(self.partner1_pk)))
        test_file.close()

        client = Client()
        session = client.session
        client.login(username=self.staff_user.username, password='staff')

        with open('accesscodes.csv', 'r') as csv_file:
            response = client.post(self.url, {'access_code_csv': csv_file})

        access_codes = AccessCode.objects.all()
        self.assertEqual(access_codes.count(), 2)


    def test_staff_dashboard_formatting(self):
        """
        An incorrectly formatted csv shouldn't upload anything.
        """
        test_file = open('accesscodes.csv', 'wb')
        csv_writer = csv.writer(test_file, lineterminator='\n')
        csv_writer.writerow(('ABCD-EFGH-IJKL', 'EBSCO'))
        csv_writer.writerow(('BBCD-EFGH-IJKL', 'JSTOR'))
        csv_writer.writerow(('ABCD-EFGH-IJKL', 'BMJ'))
        test_file.close()

        client = Client()
        session = client.session
        client.login(username=self.staff_user.username, password='staff')

        with open('accesscodes.csv', 'r') as csv_file:
            response = client.post(self.url, {'access_code_csv': csv_file})

        access_codes = AccessCode.objects.all()
        self.assertEqual(access_codes.count(), 0)