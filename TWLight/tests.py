import random
from unittest.mock import patch
from datetime import date, timedelta
from faker import Faker

from django.contrib.auth import logout
from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.test import TestCase, RequestFactory, Client
from django.utils import timezone
from django.utils.html import escape

from rest_framework.test import APIRequestFactory, force_authenticate

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.resources.tests import EditorCraftRoom
from TWLight.resources.factories import PartnerFactory
from TWLight.resources.models import AccessCode, Partner
from TWLight.users.helpers.authorizations import get_all_bundle_authorizations
from TWLight.users.factories import UserFactory, EditorFactory
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Authorization
import TWLight.users.views

from . import views as base_views

from .view_mixins import (
    PartnerCoordinatorOrSelf,
    CoordinatorsOnly,
    EditorsOnly,
    EligibleEditorsOnly,
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


class TestPartnerCoordinatorOrSelf(PartnerCoordinatorOrSelf, ObjGet, DispatchProvider):
    pass


class TestCoordinatorsOnly(CoordinatorsOnly, DispatchProvider):
    pass


class TestEditorsOnly(EditorsOnly, DispatchProvider):
    pass


class TestEligibleEditorsOnly(EligibleEditorsOnly, DispatchProvider):
    pass


class TestSelfOnly(SelfOnly, ObjGet, DispatchProvider):
    pass


class TestToURequired(ToURequired, DispatchProvider):
    pass


class TestEmailRequired(EmailRequired, DispatchProvider):
    pass


class ViewMixinTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Some mixins add messages; don't make the tests fail simply because
        # MessageMiddleware is unavailable.
        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.message_patcher.stop()

    def tearDown(self):
        for user in User.objects.all():
            user.delete()

    def test_coordinators_or_self_1(self):
        """
        PartnerCoordinatorOrSelf should allow coordinators.
        """
        user = UserFactory()
        coordinators.user_set.add(user)

        req = RequestFactory()
        req.user = user

        test = TestPartnerCoordinatorOrSelf()

        # Should not raise error.
        # test.dispatch(req)
        pass

    def test_coordinators_or_self_2(self):
        """
        PartnerCoordinatorOrSelf should allow superusers.
        """
        user = UserFactory(is_superuser=True)

        req = RequestFactory()
        req.user = user

        test = TestPartnerCoordinatorOrSelf()

        test.dispatch(req)

    def test_coordinators_or_self_3(self):
        """
        PartnerCoordinatorOrSelf should users who are the same as the view's user,
        if view.get_object returns a user.
        """
        user = UserFactory()

        req = RequestFactory()
        req.user = user

        test = TestPartnerCoordinatorOrSelf(obj=user)

        test.dispatch(req)

    def test_coordinators_or_self_4(self):
        """
        PartnerCoordinatorOrSelf should users who own the object returned by the
        view's get_object.
        """
        user = UserFactory()
        editor = EditorFactory(user=user)

        req = RequestFactory()
        req.user = user

        test = TestPartnerCoordinatorOrSelf(obj=editor)

        test.dispatch(req)

    def test_coordinators_or_self_5(self):
        """
        PartnerCoordinatorOrSelf should not allow users who fail all of the above
        criteria.
        """
        user = UserFactory(is_superuser=False)

        req = RequestFactory()
        req.user = user

        test = TestPartnerCoordinatorOrSelf(obj=None)

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

    def test_eligible_editors_only_1(self):
        """
        EligibleEditorsOnly allows eligible editors.
        """
        user = UserFactory()
        _ = EditorFactory(user=user)
        _.wp_bundle_eligible = True

        req = RequestFactory()
        req.user = user

        test = TestEligibleEditorsOnly()
        test.dispatch(req)

    def test_eligible_editors_only_2(self):
        """
        EligibleEditorsOnly does *not* allow superusers who aren't editors.
        """
        user = UserFactory(is_superuser=True)
        self.assertFalse(hasattr(user, "editor"))

        req = RequestFactory()
        req.user = user

        test = TestEligibleEditorsOnly()
        with self.assertRaises(PermissionDenied):
            test.dispatch(req)

    def test_eligible_editors_only_3(self):
        """
        EligibleEditorsOnly does not allow non-superusers who aren't editors.
        """
        user = UserFactory(is_superuser=False)
        self.assertFalse(hasattr(user, "editor"))

        req = RequestFactory()
        req.user = user

        test = TestEligibleEditorsOnly()
        with self.assertRaises(PermissionDenied):
            test.dispatch(req)

    def test_eligible_editors_only_4(self):
        """
        EligibleEditorsOnly redirects ineligible editors.
        """
        user = UserFactory(is_superuser=False)
        self.assertFalse(hasattr(user, "editor"))
        _ = EditorFactory(user=user)
        _.wp_bundle_eligible = False

        req = RequestFactory()
        req.user = user

        test = TestEligibleEditorsOnly()

        resp = test.dispatch(req)
        # This test doesn't deny permission; it sends people to my_library.
        self.assertTrue(isinstance(resp, HttpResponseRedirect))

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

    def test_email_required_for_superuser(self):
        """
        EmailRequired allows superusers (even without email)
        """
        user = UserFactory(email="", is_superuser=True)

        req = RequestFactory()
        req.user = user
        req.path = "/"

        test = TestEmailRequired()

        test.dispatch(req)

    def test_email_required_for_normal_user(self):
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
        # Lowering number of sample data created because commands take a while
        # to execute
        call_command("user_example_data", "5")
        call_command("resources_example_data", "15")
        call_command("applications_example_data", "25")


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

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.partner1 = PartnerFactory(
            authorization_method=Partner.EMAIL, status=Partner.AVAILABLE
        )
        cls.partner2 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE,
            requested_access_duration=True,
        )
        cls.partner3 = PartnerFactory(
            authorization_method=Partner.CODES, status=Partner.AVAILABLE
        )
        cls.partner4 = PartnerFactory(
            authorization_method=Partner.EMAIL, status=Partner.AVAILABLE
        )
        cls.partner5 = PartnerFactory(
            authorization_method=Partner.EMAIL,
            status=Partner.AVAILABLE,
        )

        cls.editor1 = EditorFactory()
        cls.editor1.user.email = Faker(random.choice(settings.FAKER_LOCALES)).email()
        cls.editor1.user.save()
        cls.editor2 = EditorFactory()
        cls.editor3 = EditorFactory()
        # Editor 4 is a coordinator with a session.
        cls.editor4 = EditorCraftRoom(cls, Terms=True, Coordinator=True)
        # Editor 4 is the designated coordinator for all partners.
        cls.partner1.coordinator = cls.editor4.user
        cls.partner1.account_length = timedelta(days=180)
        cls.partner1.target_url = "http://test.localdomain"
        cls.partner1.save()
        cls.partner2.coordinator = cls.editor4.user
        cls.partner2.save()
        cls.partner3.coordinator = cls.editor4.user
        cls.partner3.save()
        cls.partner4.coordinator = cls.editor4.user
        cls.partner4.save()
        cls.partner5.coordinator = cls.editor4.user
        cls.partner5.save()

        # Editor 5 is a coordinator without a session and with no designated partners.
        cls.editor5 = EditorFactory()
        coordinators.user_set.add(cls.editor5.user)

        # Create applications.
        cls.app1 = ApplicationFactory(
            editor=cls.editor1, partner=cls.partner1, status=Application.PENDING
        )
        cls.app2 = ApplicationFactory(
            editor=cls.editor2, partner=cls.partner1, status=Application.PENDING
        )
        cls.app3 = ApplicationFactory(
            editor=cls.editor3, partner=cls.partner1, status=Application.PENDING
        )
        cls.app4 = ApplicationFactory(
            editor=cls.editor1, partner=cls.partner2, status=Application.PENDING
        )
        cls.app5 = ApplicationFactory(
            editor=cls.editor2, partner=cls.partner2, status=Application.PENDING
        )
        cls.app6 = ApplicationFactory(
            editor=cls.editor3, partner=cls.partner2, status=Application.PENDING
        )
        cls.app7 = ApplicationFactory(
            editor=cls.editor1, partner=cls.partner3, status=Application.PENDING
        )
        cls.app8 = ApplicationFactory(
            editor=cls.editor1, partner=cls.partner4, status=Application.PENDING
        )
        cls.app9 = ApplicationFactory(
            editor=cls.editor2, partner=cls.partner3, status=Application.PENDING
        )
        cls.app10 = ApplicationFactory(
            editor=cls.editor1,
            partner=cls.partner5,
            status=Application.PENDING,
        )
        cls.app11 = ApplicationFactory(
            editor=cls.editor1,
            partner=cls.partner5,
            status=Application.PENDING,
        )

        # Editor 4 will update status on applications to partners 1, 2, and 5.
        # Send the application
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app1.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        cls.app1.refresh_from_db()
        cls.auth_app1 = Authorization.objects.get(
            authorizer=cls.editor4.user, user=cls.editor1.user, partners=cls.partner1
        )
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app10.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        cls.app10.refresh_from_db()
        cls.auth_app10 = Authorization.objects.get(
            authorizer=cls.editor4.user,
            user=cls.editor1.user,
            partners=cls.partner5,
        )
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app11.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        cls.app11.refresh_from_db()
        cls.auth_app11 = Authorization.objects.get(
            authorizer=cls.editor4.user,
            user=cls.editor1.user,
            partners=cls.partner5,
        )

        # Send the application
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app2.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        cls.app2.refresh_from_db()
        cls.auth_app2 = Authorization.objects.get(
            authorizer=cls.editor4.user, user=cls.editor2.user, partners=cls.partner1
        )

        # Send the application
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app3.pk}),
            data={"status": Application.SENT},
            follow=True,
        )
        cls.app3.refresh_from_db()
        cls.auth_app3 = Authorization.objects.get(
            authorizer=cls.editor4.user, user=cls.editor3.user, partners=cls.partner1
        )

        # PROXY authorization methods don't set .SENT on the evaluate page;
        # .APPROVED will automatically update them to .SENT

        # This app was created with a factory, which doesn't create a revision.
        # Let's update the status so that we have one.
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app4.pk}),
            data={"status": Application.QUESTION},
            follow=True,
        )
        # Approve the application
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app4.pk}),
            data={"status": Application.APPROVED},
            follow=True,
        )

        cls.app4.refresh_from_db()
        cls.auth_app4 = Authorization.objects.get(
            authorizer=cls.editor4.user, user=cls.editor1.user, partners=cls.partner2
        )

        # This app was created with a factory, which doesn't create a revision.
        # Let's update the status so that we have one.
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app5.pk}),
            data={"status": Application.QUESTION},
            follow=True,
        )
        # Approve the application
        cls.client.post(
            reverse("applications:evaluate", kwargs={"pk": cls.app5.pk}),
            data={"status": Application.APPROVED},
            follow=True,
        )
        cls.app5.refresh_from_db()
        cls.auth_app5 = Authorization.objects.get(
            authorizer=cls.editor4.user, user=cls.editor2.user, partners=cls.partner2
        )

        # Set up an access code to distribute
        cls.access_code = AccessCode(code="ABCD-EFGH-IJKL", partner=cls.partner3)
        cls.access_code.save()

        cls.message_patcher = patch("TWLight.applications.views.messages.add_message")
        cls.message_patcher.start()

    def tearDown(self):
        super().tearDown()
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

    def test_authorization_backfill_expiry_date_on_partner_save_with_coordinator_deletion(
        self,
    ):
        # As above, but this should still work in the case that an authorization's
        # coordinator deleted their data after authorizing a user.
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

        # Now have partner2's coordinator delete their data
        delete_url = reverse("users:delete_data", kwargs={"pk": self.editor4.user.pk})

        # Need a password so we can login
        self.editor4.user.set_password("editor")
        self.editor4.user.save()

        self.client = Client()
        session = self.client.session
        self.client.login(username=self.editor4.user, password="editor")

        submit = self.client.post(delete_url)

        # We get a strange error if we don't refresh the object first.
        self.partner2.refresh_from_db()

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

    def test_authorization_backfill_expiry_date_on_partner_save_with_new_coordinator(
        self,
    ):
        # As above, but this should still work in the case that the coordinator
        # for a partner has changed, so Authorizer is no longer in the coordinators
        # user group.
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

        # editor4 stops being a coordinator
        get_coordinators().user_set.remove(self.editor4.user)

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

    def test_authorization_authorizer_validation(self):
        """
        When an Authorization is created, we validate that
        the authorizer field is set to a user with an expected
        group.
        """
        user = UserFactory()
        coordinator_editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        auth = Authorization(user=user, authorizer=coordinator_editor.user)
        try:
            auth.save()
        except ValidationError:
            self.fail("Authorization authorizer validation failed.")

    def test_authorization_authorizer_validation_staff(self):
        """
        The authorizer can be a staff member but not a coordinator.
        """
        user = UserFactory()
        user2 = UserFactory()
        user2.is_staff = True
        user2.save()

        auth = Authorization(user=user, authorizer=user2)
        try:
            auth.save()
        except ValidationError:
            self.fail("Authorization authorizer validation failed.")

    def test_authorization_authorizer_fails_validation(self):
        """
        Attempting to create an authorization with a non-coordinator
        and non-staff user should raise a ValidationError.
        """
        user = UserFactory()
        user2 = UserFactory()

        auth = Authorization(user=user, authorizer=user2)
        with self.assertRaises(ValidationError):
            auth.save()

    def test_authorization_authorizer_can_be_updated(self):
        """
        After successfully creating a valid Authorization,
        we should be able to remove the authorizer from
        the expected user groups and still save the object.
        """
        user = UserFactory()
        coordinator_editor = EditorCraftRoom(self, Terms=True, Coordinator=True)

        auth = Authorization(user=user, authorizer=coordinator_editor.user)
        auth.save()

        coordinators = get_coordinators()
        coordinators.user_set.remove(coordinator_editor.user)

        try:
            auth.save()
        except ValidationError:
            self.fail("Authorization authorizer validation failed.")


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
            {"wp_username": self.editor1.wp_username},
            {"wp_username": self.editor2.wp_username},
            {"wp_username": self.editor3.wp_username},
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
            {"wp_username": self.editor1.wp_username},
            {"wp_username": self.editor2.wp_username},
        ]

        self.assertEqual(response.data, expected_json)

    def test_authorized_users_api_bundle(self):
        """
        With the addition of Bundle partners, the API
        should still return the correct list of authorized
        users.
        """
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)
        bundle_partner_2 = PartnerFactory(authorization_method=Partner.BUNDLE)

        self.editor1.wp_bundle_eligible = True
        self.editor1.user.last_login = timezone.now()
        self.editor1.user.save()
        self.editor1.save()
        self.editor1.update_bundle_authorization()

        # Verify we created the bundle auth as expected
        self.assertEqual(get_all_bundle_authorizations().count(), 1)

        factory = APIRequestFactory()
        request = factory.get("/api/v0/users/authorizations/partner/1")
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(
            request, bundle_partner_1.pk, 0
        )

        expected_json = [{"wp_username": self.editor1.wp_username}]

        self.assertEqual(response.data, expected_json)

    def test_authorized_users_api_bundle_inactive_user(self):
        """
        With the addition of Bundle partners, the API
        should still return the correct list of authorized
        users. This time, the list should be empty because
        the user hasn't been active in the last two weeks
        """
        bundle_partner_1 = PartnerFactory(authorization_method=Partner.BUNDLE)

        self.editor1.wp_bundle_eligible = True
        # The user had last logged in three weeks ago
        self.editor1.user.last_login = timezone.now() - timedelta(weeks=3)
        self.editor1.user.save()
        self.editor1.save()
        self.editor1.update_bundle_authorization()

        # Verify we created the bundle auth as expected
        self.assertEqual(get_all_bundle_authorizations().count(), 1)

        factory = APIRequestFactory()
        request = factory.get("/api/v0/users/authorizations/partner/1")
        force_authenticate(request, user=self.editor1.user)

        response = TWLight.users.views.AuthorizedUsers.as_view()(
            request, bundle_partner_1.pk, 0
        )

        # Returned list should be empty because of the applied filter
        expected_json = []

        self.assertEqual(response.data, expected_json)


class TestBaseViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner1 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE,
            featured=True,
            new_tags={"tags": ["music_tag"]},
        )
        cls.partner2 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE,
            requested_access_duration=True,
            new_tags={"tags": ["art_tag"]},
        )
        cls.partner3 = PartnerFactory(
            authorization_method=Partner.CODES,
            status=Partner.AVAILABLE,
            featured=True,
            new_tags={"tags": ["music_tag"]},
        )
        cls.partner4 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE,
            featured=True,
            new_tags={"tags": ["art_tag"]},
        )
        cls.partner5 = PartnerFactory(
            authorization_method=Partner.PROXY,
            status=Partner.AVAILABLE,
            new_tags={"tags": ["multidisciplinary_tag"]},
        )
        cls.user_editor = UserFactory(username="Jon Snow")
        cls.editor1 = EditorFactory(user=cls.user_editor)
        cls.editor1.wp_bundle_eligible = True
        cls.editor1.save()

    def test_featured_partners(self):
        """
        Test to determine that the carousel filters are working properly.
        When an anonymous user navigates to the homepage, only the featured
        partners should appear in the carousel.
        """
        factory = RequestFactory()
        request = factory.get(reverse("homepage"))
        request.user = AnonymousUser()
        response = base_views.NewHomePageView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        self.assertIn(escape(self.partner1.company_name), content)
        self.assertIn(escape(self.partner3.company_name), content)
        self.assertIn(escape(self.partner4.company_name), content)

        self.assertNotIn(escape(self.partner2.company_name), content)
        self.assertNotIn(escape(self.partner5.company_name), content)

    def test_filter_partners_carousel_music(self):
        """
        Test to determine that the carousel filters are working properly.
        When an anonymous user filters by a tag, only partners with that tag and
        the "multidisciplinary_tag" should appear
        """
        factory = RequestFactory()
        url = reverse("homepage")
        param_url = "{url}?tags=music_tag".format(url=url)
        request = factory.get(param_url)
        request.user = AnonymousUser()
        response = base_views.NewHomePageView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        self.assertIn(escape(self.partner1.company_name), content)
        self.assertIn(escape(self.partner3.company_name), content)
        self.assertIn(escape(self.partner5.company_name), content)

        self.assertNotIn(escape(self.partner2.company_name), content)
        self.assertNotIn(escape(self.partner4.company_name), content)

    def test_filter_partners_carousel_art(self):
        """
        Test to determine that the carousel filters are working properly.
        When an anonymous user filters by a tag, only partners with that tag and
        the "multidisciplinary_tag" should appear
        """
        factory = RequestFactory()
        url = reverse("homepage")
        param_url = "{url}?tags=art_tag".format(url=url)
        request = factory.get(param_url)
        request.user = AnonymousUser()
        response = base_views.NewHomePageView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        self.assertIn(escape(self.partner2.company_name), content)
        self.assertIn(escape(self.partner4.company_name), content)
        self.assertIn(escape(self.partner5.company_name), content)

        self.assertNotIn(escape(self.partner1.company_name), content)
        self.assertNotIn(escape(self.partner3.company_name), content)
