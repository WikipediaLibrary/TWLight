import random
from unittest.mock import patch
from datetime import date, timedelta
from faker import Faker
from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory


from rest_framework.test import APIRequestFactory, force_authenticate

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.tests import EditorCraftRoom
from TWLight.resources.factories import PartnerFactory, StreamFactory
from TWLight.resources.models import AccessCode, Partner
from TWLight.users.factories import UserFactory, EditorFactory
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Authorization
import TWLight.users.views

from .view_mixins import (
    CoordinatorOrSelf,
    CoordinatorsOnly,
    EditorsOnly,
    SelfOnly,
    ToURequired,
    EmailRequired,
)


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
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
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
        # test.dispatch(req)
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
        self.assertFalse(hasattr(user, "editor"))

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
        self.assertFalse(hasattr(user, "editor"))

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
        user = UserFactory(username="alice")

        req = RequestFactory()
        req.user = user

        test = TestSelfOnly(obj=None)

        with self.assertRaises(PermissionDenied):
            test.dispatch(req)

        user2 = UserFactory(username="bob")
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
        req.path = "/"

        test = TestToURequired()

        test.dispatch(req)

    def test_tou_required_2(self):
        """
        ToURequired allows superusers.
        """
        user = UserFactory(is_superuser=True)

        req = RequestFactory()
        req.user = user
        req.path = "/"

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
        req.path = "/"

        test = TestToURequired()

        resp = test.dispatch(req)
        # This test doesn't deny permission; it asks people to agree with the
        # terms of use.
        self.assertTrue(isinstance(resp, HttpResponseRedirect))

    def test_email_required_1(self):
        """
        EmailRequired allows users who have an email on file.
        """
        user = UserFactory(email="definitely@has.email.com")

        req = RequestFactory()
        req.user = user
        # EmailRequired expects the request to have a path that it will use to
        # construct a next parameter. Doesn't matter what it is, but it needs
        # to exist.
        req.path = "/"

        test = TestEmailRequired()

        test.dispatch(req)

    def test_email_required_2(self):
        """
        EmailRequired allows superusers (even without email)
        """
        user = UserFactory(email="", is_superuser=True)

        req = RequestFactory()
        req.user = user
        req.path = "/"

        test = TestEmailRequired()

        test.dispatch(req)

    def test_email_required_2(self):
        """
        EmailRequired disallows users who fail the above criteria.
        """
        user = UserFactory(email="", is_superuser=False)

        req = RequestFactory()
        req.user = user
        req.path = "/"

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

        call_command("user_example_data", "200")
        call_command("resources_example_data", "50")
        call_command("applications_example_data", "300")


class UserRenewalNoticeTest(TestCase):
    """
    Test the user renewal notice management command
    """

    def test_command_output(self):
        call_command("user_renewal_notice")


class AuthorizationBaseTestCase(TestCase):
    """
    Setup class for Authorization Object tests.
    Could possibly achieve the same effect via a new factory class.
    """

    def setUp(self):
        super(AuthorizationBaseTestCase, self).setUp()

        self.partner1 = PartnerFactory(
            authorization_method=Partner.EMAIL, status=Partner.AVAILABLE
        )
        self.partner2 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE,
            requested_access_duration=True,
        )
        self.partner3 = PartnerFactory(
            authorization_method=Partner.CODES, status=Partner.AVAILABLE
        )
        self.partner4 = PartnerFactory(
            authorization_method=Partner.EMAIL, status=Partner.AVAILABLE
        )
        self.partner5 = PartnerFactory(
            authorization_method=Partner.EMAIL,
            status=Partner.AVAILABLE,
            specific_stream=True,
        )
        self.partner5_stream1 = StreamFactory(
            partner=self.partner5, authorization_method=Partner.EMAIL
        )
        self.partner5_stream2 = StreamFactory(
            partner=self.partner5, authorization_method=Partner.EMAIL
        )

        self.editor1 = EditorFactory()
        self.editor1.user.email = Faker(random.choice(settings.FAKER_LOCALES)).email()
        self.editor1.user.save()
        self.editor2 = EditorFactory()
        self.editor3 = EditorFactory()
        # Editor 4 is a coordinator with a session.
        self.editor4 = EditorCraftRoom(self, Terms=True, Coordinator=True)
        # Editor 4 is the designated coordinator for all partners.
        self.partner1.coordinator = self.editor4.user
        self.partner1.account_length = timedelta(days=180)
        self.partner1.target_url = "http://test.localdomain"
        self.partner1.save()
        self.partner2.coordinator = self.editor4.user
        self.partner2.save()
        self.partner3.coordinator = self.editor4.user
        self.partner3.save()
        self.partner4.coordinator = self.editor4.user
        self.partner4.save()
        self.partner5.coordinator = self.editor4.user
        self.partner5.save()

        # Editor 5 is a coordinator without a session and with no designated partners.
        self.editor5 = EditorFactory()
        coordinators.user_set.add(self.editor5.user)

        # Create applications.
        self.app1 = ApplicationFactory(
            editor=self.editor1, partner=self.partner1, status=Application.PENDING
        )
        self.app2 = ApplicationFactory(
            editor=self.editor2, partner=self.partner1, status=Application.PENDING
        )
        self.app3 = ApplicationFactory(
            editor=self.editor3, partner=self.partner1, status=Application.PENDING
        )
        self.app4 = ApplicationFactory(
            editor=self.editor1, partner=self.partner2, status=Application.PENDING
        )
        self.app5 = ApplicationFactory(
            editor=self.editor2, partner=self.partner2, status=Application.PENDING
        )
        self.app6 = ApplicationFactory(
            editor=self.editor3, partner=self.partner2, status=Application.PENDING
        )
        self.app7 = ApplicationFactory(
            editor=self.editor1, partner=self.partner3, status=Application.PENDING
        )
        self.app8 = ApplicationFactory(
            editor=self.editor1, partner=self.partner4, status=Application.PENDING
        )
        self.app9 = ApplicationFactory(
            editor=self.editor2, partner=self.partner3, status=Application.PENDING
        )
        self.app10 = ApplicationFactory(
            editor=self.editor1,
            partner=self.partner5,
            specific_stream=self.partner5_stream1,
            status=Application.PENDING,
        )
        self.app11 = ApplicationFactory(
            editor=self.editor1,
            partner=self.partner5,
            specific_stream=self.partner5_stream2,
            status=Application.PENDING,
        )

        # Editor 4 will update status on applications to partners 1, 2, and 5.
        # Send the application
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app1.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        self.app1.refresh_from_db()
        self.auth_app1 = Authorization.objects.get(
            authorizer=self.editor4.user, user=self.editor1.user, partners=self.partner1
        )
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app10.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        self.app10.refresh_from_db()
        self.auth_app10 = Authorization.objects.get(
            authorizer=self.editor4.user,
            user=self.editor1.user,
            partners=self.partner5,
            stream=self.partner5_stream1,
        )
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app11.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        self.app11.refresh_from_db()
        self.auth_app11 = Authorization.objects.get(
            authorizer=self.editor4.user,
            user=self.editor1.user,
            partners=self.partner5,
            stream=self.partner5_stream2,
        )

        # Approve the application
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app2.pk}),
            data={"status": Application.APPROVED},
            follow=True,
        )
        self.app2.refresh_from_db()
        self.auth_app2 = Authorization(
            authorizer=self.editor4.user, user=self.editor2.user
        )
        self.auth_app2.save()
        self.auth_app2.partners.add(self.partner1)

        # Send the application
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app3.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        self.app3.refresh_from_db()
        self.auth_app3 = Authorization.objects.get(
            authorizer=self.editor4.user, user=self.editor3.user, partners=self.partner1
        )

        # PROXY authorization methods don't set .SENT on the evaluate page;
        # .APPROVED will automatically update them to .SENT

        # This app was created with a factory, which doesn't create a revision.
        # Let's update the status so that we have one.
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app4.pk}),
            data={"status": Application.QUESTION},
            follow=True,
        )
        # Approve the application
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app4.pk}),
            data={"status": Application.APPROVED},
            follow=True,
        )

        self.app4.refresh_from_db()
        self.auth_app4 = Authorization.objects.get(
            authorizer=self.editor4.user, user=self.editor1.user, partners=self.partner2
        )

        # This app was created with a factory, which doesn't create a revision.
        # Let's update the status so that we have one.
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app5.pk}),
            data={"status": Application.QUESTION},
            follow=True,
        )
        # Approve the application
        self.client.post(
            reverse("applications:evaluate", kwargs={"pk": self.app5.pk}),
            data={"status": Application.APPROVED},
            follow=True,
        )
        self.app5.refresh_from_db()
        self.auth_app5 = Authorization.objects.get(
            authorizer=self.editor4.user, user=self.editor2.user, partners=self.partner2
        )

        # Set up an access code to distribute
        self.access_code = AccessCode(code="ABCD-EFGH-IJKL", partner=self.partner3)
        self.access_code.save()

        self.message_patcher = patch("TWLight.applications.views.messages.add_message")
        self.message_patcher.start()

    def tearDown(self):
        super(AuthorizationBaseTestCase, self).tearDown()
        self.partner1.delete()
        self.partner2.delete()
        self.partner3.delete()
        self.partner4.delete()
        self.partner5.delete()
        self.access_code.delete()
        self.editor1.delete()
        self.editor2.delete()
        self.editor3.delete()
        self.editor4.delete()
        self.app1.delete()
        self.app2.delete()
        self.app3.delete()
        self.app4.delete()
        self.app5.delete()
        self.app6.delete()
        self.app7.delete()
        self.app8.delete()
        self.app9.delete()
        self.app10.delete()
        self.app11.delete()


class AuthorizationTestCase(AuthorizationBaseTestCase):
    """
    Tests that Authorizations are correctly created and updated based on user activity.
    """

    def test_approval_sets_properties(self):
        """
        Test that authorizer is correctly set.
        """
        self.assertTrue(self.auth_app1)
        self.assertTrue(self.auth_app2)
        self.assertTrue(self.auth_app3)
        self.assertTrue(self.auth_app4)
        self.assertTrue(self.auth_app5)

    def test_authorizations_codes(self):
        # In the distribution_method == CODES case, make sure that
        # an authorization object with the correct information is
        # created after a coordinator marks an application as sent.

        authorization_object_exists = Authorization.objects.filter(
            user=self.app7.user,
            authorizer=self.editor4.user,
            partners=self.app7.partner,
        ).exists()

        self.assertFalse(authorization_object_exists)

        request = RequestFactory().post(
            reverse("applications:send_partner", kwargs={"pk": self.app7.partner.pk}),
            data={
                "accesscode": [
                    "{app_pk}_{code}".format(
                        app_pk=self.app7.pk, code=self.access_code.code
                    )
                ]
            },
        )
        request.user = self.editor4.user

        _ = TWLight.applications.views.SendReadyApplicationsView.as_view()(
            request, pk=self.app7.partner.pk
        )

        authorization_object_exists = Authorization.objects.filter(
            user=self.app7.user,
            authorizer=self.editor4.user,
            partners=self.app7.partner,
        ).exists()

        self.assertTrue(authorization_object_exists)

    def test_authorizations_email(self):
        # In the distribution_method == EMAIL case, make sure that
        # an authorization object with the correct information is
        # created after a coordinator marks an application as sent.

        authorization_object_exists = Authorization.objects.filter(
            user=self.app8.user,
            authorizer=self.editor4.user,
            partners=self.app8.partner,
        ).exists()

        self.assertFalse(authorization_object_exists)

        request = RequestFactory().post(
            reverse("applications:send_partner", kwargs={"pk": self.app8.partner.pk}),
            data={"applications": [self.app8.pk]},
        )
        request.user = self.editor4.user

        _ = TWLight.applications.views.SendReadyApplicationsView.as_view()(
            request, pk=self.app8.partner.pk
        )

        authorization_object_exists = Authorization.objects.filter(
            user=self.app8.user,
            authorizer=self.editor4.user,
            partners=self.app8.partner,
        ).exists()

        self.assertTrue(authorization_object_exists)

    def test_handle_stream_post_delete(self):

        partner5_authorizations = Authorization.objects.filter(
            partners=self.partner5, user=self.editor1.user, stream__isnull=True
        )
        stream1_authorizations = Authorization.objects.filter(
            partners=self.partner5, user=self.editor1.user, stream=self.partner5_stream1
        )
        stream2_authorizations = Authorization.objects.filter(
            partners=self.partner5, user=self.editor1.user, stream=self.partner5_stream2
        )
        # Verifying that we only have stream-specific auths.
        self.assertTrue(self.partner5.specific_stream)
        self.assertEquals(partner5_authorizations.count(), 0)
        self.assertEquals(stream1_authorizations.count(), 1)
        self.assertEquals(stream2_authorizations.count(), 1)

        # Deleting stream 1 should convert its related auths to partner scope.
        self.partner5_stream1.delete()
        self.assertTrue(self.partner5.specific_stream)
        stream1_authorizations.all()
        partner5_authorizations.all()
        self.assertEqual(partner5_authorizations.count(), 1)
        self.assertEquals(stream1_authorizations.count(), 0)

        # Deleting stream 2 shouldn't create a duplicate partner-scoped auth. The extra auth should just disappear.
        # Since stream 2 was the last stream related to partner 5, partner5.specific_stream should now be False.
        self.partner5_stream2.delete()
        self.assertFalse(self.partner5.specific_stream)
        stream2_authorizations.all()
        partner5_authorizations.all()
        self.assertEqual(partner5_authorizations.count(), 1)
        self.assertEquals(stream2_authorizations.count(), 0)

    def test_updating_existing_authorization(self):
        """
        In the case that an authorization already exists for a user,
        and they apply for renewal, their authorization object should
        be updated with any new information (e.g. authorizer).
        """

        # Revalidate starting authorizer.
        self.assertEqual(self.auth_app1.authorizer, self.editor4.user)

        # Create a new application to the same partner (in reality this
        # is most likely to be a renewal)
        app1_renewal = ApplicationFactory(
            editor=self.app1.user.editor, partner=self.app1.partner
        )
        app1_renewal.status = Application.APPROVED
        app1_renewal.save()

        # Assign a new coordinator to this partner
        app1_renewal.partner.coordinator = self.editor5.user
        app1_renewal.partner.save()

        # And mark this one as sent, but by a different user.
        request = RequestFactory().post(
            reverse(
                "applications:send_partner", kwargs={"pk": app1_renewal.partner.pk}
            ),
            data={"applications": [app1_renewal.pk]},
        )
        request.user = self.editor5.user

        _ = TWLight.applications.views.SendReadyApplicationsView.as_view()(
            request, pk=app1_renewal.partner.pk
        )

        auth_app1_renewal = Authorization.objects.get(
            user=self.app1.user,
            authorizer=self.editor5.user,
            partners=self.app1.partner,
        )
        self.assertTrue(auth_app1_renewal)

    def test_access_codes_email(self):
        # For access code partners, when applications are marked sent,
        # access codes should be sent automatically via email.

        # outbox already has messages in the outbox from creating approved
        # applications during setup. So let's get a starting count.
        starting_message_count = len(mail.outbox)

        request = RequestFactory().post(
            reverse("applications:send_partner", kwargs={"pk": self.app9.partner.pk}),
            data={
                "accesscode": [
                    "{app_pk}_{code}".format(
                        app_pk=self.app9.pk, code=self.access_code.code
                    )
                ]
            },
        )
        request.user = self.editor4.user

        # Mark as sent
        response = TWLight.applications.views.SendReadyApplicationsView.as_view()(
            request, pk=self.app9.partner.pk
        )
        # verify that was successful
        self.assertEqual(response.status_code, 302)

        # We expect one additional email should now be sent.
        self.assertEqual(len(mail.outbox), starting_message_count + 1)

        # The most recent email should contain the assigned access code.
        self.assertTrue(self.access_code.code in mail.outbox[-1].body)

    def test_authorization_expiry_date(self):
        # For a partner with a set account length we should set the expiry
        # date correctly for its authorizations.

        expected_expiry = date.today() + self.app1.partner.account_length
        self.assertEqual(self.auth_app1.date_expires, expected_expiry)

    def test_authorization_expiry_date_proxy(self):
        # For a proxy partner we should set the expiry
        # date correctly for its authorizations.

        expected_expiry = date.today() + timedelta(days=365)
        self.assertEqual(self.auth_app4.date_expires, expected_expiry)

    def test_authorization_backfill_expiry_date_on_partner_save(self):
        # When a proxy partner is saved, and authorizations without an expiration date should have it set correctly.
        # This comes up when partner authorization method is changed from one that has no expiration to proxy.
        # Zero partner 2 authorizations with no expiry.
        initial_partner2_auths_no_expiry_count = 0
        initial_partner2_auths_no_expiry = Authorization.objects.filter(
            partners=self.partner2, date_expires__isnull=True
        )
        for partner2_auth in initial_partner2_auths_no_expiry:
            if partner2_auth.is_valid:
                initial_partner2_auths_no_expiry_count += 1

        # Count partner 2 apps with an expiration date.
        initial_partner2_auths_with_expiry_count = 0
        initial_partner2_auths_with_expiry = Authorization.objects.filter(
            partners=self.partner2, date_expires__isnull=False
        )
        for partner2_auth in initial_partner2_auths_with_expiry:
            if partner2_auth.is_valid:
                initial_partner2_auths_with_expiry_count += 1
                # Clear out the expiration date on those.
                partner2_auth.date_expires = None
                partner2_auth.save()

        # Save partner 2
        self.partner2.save()
        self.partner2.refresh_from_db()
        # Count partner 2 apps with an expiration date post_save.
        post_save_partner2_auths_with_expiry_count = 0
        post_save_partner2_auths_with_expiry = Authorization.objects.filter(
            partners=self.partner2, date_expires__isnull=False
        )
        for partner2_auth in post_save_partner2_auths_with_expiry:
            if partner2_auth.is_valid:
                post_save_partner2_auths_with_expiry_count += 1

        # All valid partner 2 authorizations have expiry set.
        post_save_partner2_auths_no_expiry_count = Authorization.objects.filter(
            partners=self.partner2, date_expires__isnull=True
        ).count()
        self.assertEqual(
            initial_partner2_auths_with_expiry_count
            + initial_partner2_auths_no_expiry_count,
            post_save_partner2_auths_with_expiry_count,
        )

    def test_authorization_backfill_command(self):
        # The authorization backfill command should retroactively create authorizations for applications submitted
        # before we had authorizations.
        # Count the authorizations created in realtime by previous user activity.
        realtime_authorization_count = Authorization.objects.count()
        # Delete all of them.
        Authorization.objects.all().delete()
        # Zero authorizations.
        self.assertEqual(Authorization.objects.count(), 0)
        # run the backfill command
        call_command("authorization_backfill")
        # Count the authorizations created by the backfill command.
        backfill_authorization_count = Authorization.objects.count()
        # All authorizations replaced.
        self.assertEqual(realtime_authorization_count, backfill_authorization_count)


class AuthorizedUsersAPITestCase(AuthorizationBaseTestCase):
    """
    Tests for the AuthorizedUsers view and API.
    """

    def test_authorized_users_api_denied(self):
        """
        Test that, if no credentials are supplied, the API returns no data.
        """
        factory = APIRequestFactory()
        request = factory.get("/api/v0/users/authorizations/partner/1")

        response = TWLight.users.views.AuthorizedUsers.as_view()(
            request, self.partner1.pk, 0
        )

        self.assertEqual(response.status_code, 401)

    def test_authorized_users_api_success(self):
        """
        Test that, if credentials are supplied, the API returns a 200 status code.
        """
        factory = APIRequestFactory()
        request = factory.get("/api/v0/users/authorizations/partner/1")
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(
            request, self.partner1.pk, 0
        )

        self.assertEqual(response.status_code, 200)

    def test_authorized_users_api_applications(self):
        """
        In the case of a non-proxy partner, we should return all users with
        a sent application.
        """
        factory = APIRequestFactory()
        request = factory.get("/api/v0/users/authorizations/partner/1")
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(
            request, self.partner1.pk, 0
        )

        expected_json = [
            {"wp_username": self.editor1.user.editor.wp_username},
            {"wp_username": self.editor3.user.editor.wp_username},
        ]

        self.assertEqual(response.data, expected_json)

    def test_authorized_users_api_authorizations(self):
        """
        In the case of a proxy partner, we should return all active authorizations
        for that partner.
        """
        factory = APIRequestFactory()
        request = factory.get("/api/v0/users/authorizations/partner/1")
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(
            request, self.partner2.pk, 0
        )

        expected_json = [
            {"wp_username": self.editor1.user.editor.wp_username},
            {"wp_username": self.editor2.user.editor.wp_username},
        ]

        self.assertEqual(response.data, expected_json)
