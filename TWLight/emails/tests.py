from datetime import datetime, timedelta

from djmail.template_mail import MagicMailBuilder, InlineCSSTemplateMail
from unittest.mock import patch

from django_comments import get_form_target
from django_comments.models import Comment
from django_comments.signals import comment_was_posted
from django.contrib.auth import signals
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from TWLight.applications.factories import (
    ApplicationFactory,
)
from TWLight.applications.models import Application
from TWLight.resources.factories import PartnerFactory
from TWLight.resources.models import Partner
from TWLight.resources.tests import EditorCraftRoom
from TWLight.users.factories import EditorFactory, UserFactory
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Authorization

# We need to import these in order to register the signal handlers; if we don't,
# when we test that those handler functions have been called, we will get
# False even when they work in real life.
from .tasks import (
    send_comment_notification_emails,
    send_approval_notification_email,
    send_rejection_notification_email,
    send_user_renewal_notice_emails,
    send_survey_active_user_email,
)


class ApplicationCommentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.editor = EditorFactory(user__email="editor@example.com").user

        coordinators = get_coordinators()

        cls.coordinator1 = EditorFactory(
            user__email="c1@example.com", user__username="c1"
        ).user
        cls.coordinator2 = EditorFactory(
            user__email="c2@example.com", user__username="c2"
        ).user
        coordinators.user_set.add(cls.coordinator1)
        coordinators.user_set.add(cls.coordinator2)

        cls.partner = PartnerFactory()

    def _create_comment(self, app, user):
        CT = ContentType.objects.get_for_model

        comm = Comment.objects.create(
            content_type=CT(Application),
            object_pk=app.pk,
            user=user,
            user_name=user.username,
            comment="Content!",
            site=Site.objects.get_current(),
        )
        comm.save()

        return comm

    def _set_up_email_test_objects(self):
        app = ApplicationFactory(editor=self.editor.editor, partner=self.partner)

        factory = RequestFactory()
        request = factory.post(get_form_target())
        return app, request

    def test_comment_email_sending_1(self):
        """
        A coordinator posts a comment to an Editor's application and an email
        is send to that Editor. An email is not sent to the coordinator.
        """
        app, request = self._set_up_email_test_objects()
        request.user = UserFactory()

        self.assertEqual(len(mail.outbox), 0)

        comment1 = self._create_comment(app, self.coordinator1)
        comment_was_posted.send(sender=Comment, comment=comment1, request=request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.editor.email])

    def test_comment_email_sending_2(self):
        """
        After a coordinator posts a comment, the Editor posts an additional
        comment. An email is sent to the coordinator who posted the earlier
        comment. An email is not sent to the editor.
        """
        app, request = self._set_up_email_test_objects()
        request.user = UserFactory()
        self.assertEqual(len(mail.outbox), 0)

        _ = self._create_comment(app, self.coordinator1)
        comment2 = self._create_comment(app, self.editor)

        comment_was_posted.send(sender=Comment, comment=comment2, request=request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.coordinator1.email])

    def test_comment_email_sending_3(self):
        """
        After the editor and coordinator post a comment, an additional
        coordinator posts a comment. One email is sent to the first coordinator,
        and a distinct email is sent to the editor.
        """
        app, request = self._set_up_email_test_objects()
        request.user = UserFactory()
        self.assertEqual(len(mail.outbox), 0)

        _ = self._create_comment(app, self.coordinator1)
        _ = self._create_comment(app, self.editor)
        comment3 = self._create_comment(app, self.coordinator2)
        comment_was_posted.send(sender=Comment, comment=comment3, request=request)

        self.assertEqual(len(mail.outbox), 2)

        # Either order of email sending is fine.
        try:
            self.assertEqual(mail.outbox[0].to, [self.coordinator1.email])
            self.assertEqual(mail.outbox[1].to, [self.editor.email])
        except AssertionError:
            self.assertEqual(mail.outbox[1].to, [self.coordinator1.email])
            self.assertEqual(mail.outbox[0].to, [self.editor.email])

    def test_comment_email_sending_4(self):
        """
        A comment made on an application that's any further along the process
        than PENDING (i.e. a coordinator has taken some action on it) should
        fire an email to the coordinator who took the last action on it.
        """
        app, request = self._set_up_email_test_objects()
        request.user = UserFactory()
        self.assertEqual(len(mail.outbox), 0)

        # Create a coordinator with a test client session
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)

        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Approve the application
        url = reverse("applications:evaluate", kwargs={"pk": app.pk})
        response = self.client.post(
            url, data={"status": Application.QUESTION}, follow=True
        )

        comment4 = self._create_comment(app, self.editor)
        comment_was_posted.send(sender=Comment, comment=comment4, request=request)

        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(mail.outbox[0].to, [coordinator.user.email])

    def test_comment_email_sending_5(self):
        """
        A comment from the applying editor made on an application that
        has had no actions taken on it and no existing comments should
        not fire an email to anyone.
        """
        app, request = self._set_up_email_test_objects()
        request.user = UserFactory()
        self.assertEqual(len(mail.outbox), 0)

        comment5 = self._create_comment(app, self.editor)
        comment_was_posted.send(sender=Comment, comment=comment5, request=request)

        self.assertEqual(len(mail.outbox), 0)

    def test_comment_email_sending_6(self):
        """
        In case the coordinator is changed for a Partner, then the
        previous coordinator should not receive comment notification email.
        Also now the new coordinator should receive the email.
        """
        app, request = self._set_up_email_test_objects()
        request.user = UserFactory()
        self.assertEqual(len(mail.outbox), 0)

        # Setting up coordinator1 as coordinator for partner
        self.partner.coordinator = self.coordinator1
        self.partner.save()

        # Coordinator posts a comment, then Editor posts an additional comment
        # An email is sent to the coordinator who posted the earlier comment
        _ = self._create_comment(app, self.coordinator1)
        comment1 = self._create_comment(app, self.editor)
        comment_was_posted.send(sender=Comment, comment=comment1, request=request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.coordinator1.email])

        # Create a coordinator with a test client session
        # and set it as the coordinator for partner
        coordinator = EditorCraftRoom(self, Terms=True, Coordinator=True)
        self.partner.coordinator = coordinator.user
        self.partner.save()

        # Evaluate the application
        url = reverse("applications:evaluate", kwargs={"pk": app.pk})
        response = self.client.post(
            url, data={"status": Application.QUESTION}, follow=True
        )

        # Editor makes another comment
        # Now the New Coordinator will receive the Email
        comment2 = self._create_comment(app, self.editor)
        comment_was_posted.send(sender=Comment, comment=comment2, request=request)
        self.assertEqual(mail.outbox[1].to, [coordinator.user.email])

    # We'd like to mock out send_comment_notification_emails and test that
    # it is called when comment_was_posted is fired, but we can't; the signal
    # handler is attached to the real send_comment_notification_emails, not
    # the mocked one.


class ApplicationStatusTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.coordinator = EditorFactory().user
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)

    @patch("TWLight.emails.tasks.send_approval_notification_email")
    def test_approval_calls_email_function(self, mock_email):
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.APPROVED
        app.save()
        self.assertTrue(mock_email.called)

    def test_approval_does_not_call_email_for_applications_with_access_codes_partner(
        self,
    ):
        partner_with_access_codes = PartnerFactory(authorization_method=Partner.CODES)
        app_with_access_codes_partner = ApplicationFactory(
            status=Application.PENDING, partner=partner_with_access_codes
        )
        app_with_access_codes_partner.status = Application.APPROVED
        app_with_access_codes_partner.save()
        self.assertEqual(len(mail.outbox), 0)

    @patch("TWLight.emails.tasks.send_approval_notification_email")
    def test_reapproval_does_not_call_email_function(self, mock_email):
        """
        Saving an Application with APPROVED status, when it already had an
        APPROVED status, should not re-send the email.
        """
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.APPROVED
        app.save()
        app.save()
        self.assertEqual(mock_email.call_count, 1)

    @patch("TWLight.emails.tasks.send_rejection_notification_email")
    def test_rejection_calls_email_function(self, mock_email):
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.NOT_APPROVED
        app.save()
        self.assertTrue(mock_email.called)

    @patch("TWLight.emails.tasks.send_rejection_notification_email")
    def test_rerejection_does_not_call_email_function(self, mock_email):
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.NOT_APPROVED
        app.save()
        app.save()
        self.assertEqual(mock_email.call_count, 1)

    def test_pending_does_not_call_email_function(self):
        """
        Applications saved with a PENDING status should not generate email.
        """
        orig_outbox = len(mail.outbox)
        _ = ApplicationFactory(status=Application.PENDING)
        self.assertEqual(len(mail.outbox), orig_outbox)

    def test_question_does_not_call_email_function(self):
        """
        Applications saved with a QUESTION status should not generate email.
        """
        orig_outbox = len(mail.outbox)
        _ = ApplicationFactory(status=Application.QUESTION)
        self.assertEqual(len(mail.outbox), orig_outbox)

    def test_sent_does_not_call_email_function(self):
        """
        Applications saved with a SENT status should not generate email.
        """
        orig_outbox = len(mail.outbox)
        ApplicationFactory(status=Application.SENT, sent_by=self.coordinator)
        self.assertEqual(len(mail.outbox), orig_outbox)

    @patch("TWLight.emails.tasks.send_waitlist_notification_email")
    def test_waitlist_calls_email_function(self, mock_email):
        partner = PartnerFactory(status=Partner.WAITLIST)
        app = ApplicationFactory(status=Application.PENDING, partner=partner)
        self.assertTrue(mock_email.called)

        partner.delete()
        app.delete()

    @patch("TWLight.emails.tasks.send_waitlist_notification_email")
    def test_nonwaitlist_does_not_call_email_function(self, mock_email):
        partner = PartnerFactory(status=Partner.AVAILABLE)
        app = ApplicationFactory(status=Application.PENDING, partner=partner)
        self.assertFalse(mock_email.called)

        partner.delete()
        app.delete()

        partner = PartnerFactory(status=Partner.NOT_AVAILABLE)
        app = ApplicationFactory(status=Application.PENDING, partner=partner)
        self.assertFalse(mock_email.called)

        partner.delete()
        app.delete()

    @patch("TWLight.emails.tasks.send_waitlist_notification_email")
    def test_waitlisting_partner_calls_email_function(self, mock_email):
        """
        Switching a Partner to WAITLIST status should call the email function
        for apps to that partner with open statuses.
        """
        partner = PartnerFactory(status=Partner.AVAILABLE)
        app = ApplicationFactory(status=Application.PENDING, partner=partner)
        self.assertFalse(mock_email.called)

        partner.status = Partner.WAITLIST
        partner.save()
        self.assertTrue(mock_email.called)
        mock_email.assert_called_with(app)

    @patch("TWLight.emails.tasks.send_waitlist_notification_email")
    def test_waitlisting_partner_does_not_call_email_function(self, mock_email):
        """
        Switching a Partner to WAITLIST status should NOT call the email
        function for apps to that partner with closed statuses.
        """
        partner = PartnerFactory(status=Partner.AVAILABLE)
        app = ApplicationFactory(status=Application.APPROVED, partner=partner)
        app = ApplicationFactory(status=Application.NOT_APPROVED, partner=partner)
        app = ApplicationFactory(
            status=Application.SENT, partner=partner, sent_by=self.coordinator
        )
        self.assertFalse(mock_email.called)

        partner.status = Partner.WAITLIST
        partner.save()
        self.assertFalse(mock_email.called)


class UserRenewalNoticeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        editor = EditorFactory(user__email="editor@example.com")
        cls.user = editor.user

        cls.coordinator = EditorFactory().user
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)

        cls.partner = PartnerFactory()

        cls.authorization = Authorization()
        cls.authorization.user = cls.user
        cls.authorization.authorizer = cls.coordinator
        cls.authorization.date_expires = datetime.today() + timedelta(weeks=1)
        cls.authorization.save()
        cls.authorization.partners.add(cls.partner)

    def test_single_user_renewal_notice(self):
        """
        Given one authorization that expires in two weeks, ensure
        that our email task sends an email to that user.
        """
        call_command("user_renewal_notice")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_user_renewal_notice_disabled(self):
        """
        Users have the option to disable renewal notices. If users have
        disabled emails, we shouldn't send them one.
        """
        self.user.userprofile.send_renewal_notices = False
        self.user.userprofile.save()

        call_command("user_renewal_notice")

        self.assertEqual(len(mail.outbox), 0)

    def test_user_renewal_notice_doesnt_duplicate(self):
        """
        If we run the command a second time, the same user shouldn't receive
        a second email.
        """
        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 1)

        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 1)

    def test_user_renewal_notice_past_date(self):
        """
        If the authorization expired before today, the user shouldn't
        receive a notice.
        """
        self.authorization.date_expires = datetime.today() - timedelta(weeks=1)
        self.authorization.save()
        call_command("user_renewal_notice")

        self.assertEqual(len(mail.outbox), 0)

    def test_user_renewal_notice_future_date(self):
        """
        If the authorization doesn't expire for months, the user
        shouldn't receive a notice.
        """
        self.authorization.date_expires = datetime.today() + timedelta(weeks=8)
        self.authorization.save()
        call_command("user_renewal_notice")

        self.assertEqual(len(mail.outbox), 0)

    def test_user_renewal_notice_future_date_1(self):
        """
        If we have multiple authorizations to send emails for, let's make
        sure we send distinct emails to the right places.
        """
        editor2 = EditorFactory(user__email="editor2@example.com")

        authorization2 = Authorization()
        authorization2.user = editor2.user
        authorization2.authorizer = self.coordinator
        authorization2.date_expires = datetime.today() + timedelta(weeks=1)
        authorization2.save()
        authorization2.partners.add(self.partner)

        call_command("user_renewal_notice")

        self.assertEqual(len(mail.outbox), 2)

        # Make sure that the two emails went to the two expected
        # email addresses.
        # This looks a little complicated because mail.outbox[0].to is a
        # (one element) list, and we need to compare sets to ensure we've
        # got 1 of each email.
        self.assertEqual(
            {mail.outbox[0].to[0], mail.outbox[1].to[0]},
            {"editor@example.com", "editor2@example.com"},
        )

    def test_user_renewal_notice_after_renewal(self):
        """
        If a user renews their authorization, we want to remind
        them again when it runs out.
        """
        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 1)
        self.authorization.refresh_from_db()
        self.assertTrue(self.authorization.reminder_email_sent)

        # We already have an authorization, so let's setup up
        # an application that 'corresponds' to it.
        application = ApplicationFactory(
            editor=self.user.editor,
            sent_by=self.coordinator,
            partner=self.partner,
            status=Application.SENT,
            requested_access_duration=1,
        )
        application.save()

        # File a renewal, approve it, and send it.
        self.partner.renewals_available = True
        self.partner.save()
        renewed_app = application.renew()
        renewed_app.status = application.APPROVED
        renewed_app.save()
        renewed_app.status = application.SENT
        renewed_app.sent_by = self.coordinator
        renewed_app.save()

        # Sending this renewal notice will have sent the user
        # an email, so we expect 2 emails now.
        self.assertEqual(len(mail.outbox), 2)

        # We've correctly marked reminder_email_sent as False
        self.authorization.refresh_from_db()
        self.assertFalse(self.authorization.reminder_email_sent)

        # And calling the command should send a third email.
        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 3)

    def test_user_renewal_notice_user_already_filed_renewal(self):
        """
        Per T300014, a user shouldn't get an email if they have already filed
        for a renewal
        """
        # We already have an authorization, so let's setup up
        # an application that 'corresponds' to it.
        application = ApplicationFactory(
            editor=self.user.editor,
            sent_by=self.coordinator,
            partner=self.partner,
            status=Application.SENT,
            requested_access_duration=1,
        )
        application.save()

        # File a renewal.
        self.partner.renewals_available = True
        self.partner.save()
        renewed_app = application.renew()
        renewed_app.status = application.PENDING
        renewed_app.save()

        # Email shouldn't be sent since a renewal request has already been made
        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 0)

    def test_user_renewal_notice_user_already_filed_1_renewal(self):
        """
        Per T300014, a user shouldn't get an email if they have already filed
        for a renewal. This tests when a user has three near expiration authorizations,
        but has only filed for one renewal. Only two emails should be sent.
        """
        # We already have an authorization, so let's setup up
        # an application that 'corresponds' to it.
        application = ApplicationFactory(
            editor=self.user.editor,
            sent_by=self.coordinator,
            partner=self.partner,
            status=Application.SENT,
            requested_access_duration=1,
        )
        application.save()

        # File a renewal.
        self.partner.renewals_available = True
        self.partner.save()
        renewed_app = application.renew()
        renewed_app.status = application.PENDING
        renewed_app.save()

        # Create a new authorization
        partner2 = PartnerFactory()
        authorization2 = Authorization()
        authorization2.user = self.user
        authorization2.authorizer = self.coordinator
        authorization2.date_expires = datetime.today() + timedelta(weeks=1)
        authorization2.save()
        authorization2.partners.add(partner2)

        # Create a new authorization
        partner3 = PartnerFactory()
        authorization3 = Authorization()
        authorization3.user = self.user
        authorization3.authorizer = self.coordinator
        authorization3.date_expires = datetime.today() + timedelta(weeks=1)
        authorization3.save()
        authorization3.partners.add(partner3)

        # Only one mail should be sent since a renewal request has already been made
        # for one of the authorizations
        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 2)

    def test_user_renewal_notice_user_already_filed_2_renewals(self):
        """
        Per T300014, a user shouldn't get an email if they have already filed
        for a renewal. This tests when a user has three near expiration authorizations,
        but has only filed for two renewals. Only one email should be sent.
        """
        # We already have an authorization, so let's setup up
        # an application that 'corresponds' to it.
        application = ApplicationFactory(
            editor=self.user.editor,
            sent_by=self.coordinator,
            partner=self.partner,
            status=Application.SENT,
            requested_access_duration=1,
        )
        application.save()

        # File a renewal.
        self.partner.renewals_available = True
        self.partner.save()
        renewed_app = application.renew()
        renewed_app.status = application.PENDING
        renewed_app.save()

        # Create a new authorization
        partner2 = PartnerFactory()
        authorization2 = Authorization()
        authorization2.user = self.user
        authorization2.authorizer = self.coordinator
        authorization2.date_expires = datetime.today() + timedelta(weeks=1)
        authorization2.save()
        authorization2.partners.add(partner2)

        # Create a new authorization
        partner3 = PartnerFactory()
        authorization3 = Authorization()
        authorization3.user = self.user
        authorization3.authorizer = self.coordinator
        authorization3.date_expires = datetime.today() + timedelta(weeks=1)
        authorization3.save()
        authorization3.partners.add(partner3)

        application2 = ApplicationFactory(
            editor=self.user.editor,
            sent_by=self.coordinator,
            partner=partner3,
            status=Application.SENT,
            requested_access_duration=1,
        )
        application.save()

        partner3.renewals_available = True
        partner3.save()
        renewed_app2 = application2.renew()
        renewed_app2.status = application2.PENDING
        renewed_app2.save()

        # Only one mail should be sent since a renewal request has already been made
        # for one of the authorizations
        call_command("user_renewal_notice")
        self.assertEqual(len(mail.outbox), 1)


class CoordinatorReminderEmailTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        editor = EditorFactory()
        cls.user = editor.user
        editor2 = EditorFactory()
        cls.user2 = editor2.user

        cls.coordinator = EditorFactory(user__email="editor@example.com").user
        coordinators = get_coordinators()
        coordinators.user_set.add(cls.coordinator)

        cls.partner = PartnerFactory(coordinator=cls.coordinator)
        cls.partner2 = PartnerFactory(coordinator=cls.coordinator)

    def test_send_coordinator_reminder_email(self):
        ApplicationFactory(
            partner=self.partner, status=Application.PENDING, editor=self.user.editor
        )

        # Coordinator only wants reminders for apps under discussion
        self.coordinator.userprofile.pending_app_reminders = False
        self.coordinator.userprofile.approved_app_reminders = False
        self.coordinator.userprofile.save()

        call_command("send_coordinator_reminders")
        self.assertEqual(len(mail.outbox), 0)

        ApplicationFactory(
            partner=self.partner2, status=Application.QUESTION, editor=self.user2.editor
        )

        call_command("send_coordinator_reminders")
        self.assertEqual(len(mail.outbox), 1)
        # We include the count for all waiting (PENDING, QUESTION,
        # APPROVED) apps whenever we send an email, but trigger
        # emails only based on preferences i.e. if a coordinator
        # has enabled reminders only for QUESTION, we send a
        # reminder only when we have an app of status: QUESTION,
        # but include info on all apps in the email.
        self.assertNotIn("1 pending application", mail.outbox[0].body)
        self.assertIn("1 under discussion application", mail.outbox[0].body)
        self.assertNotIn("1 approved application", mail.outbox[0].body)

        ApplicationFactory(
            partner=self.partner, status=Application.APPROVED, editor=self.user2.editor
        )
        ApplicationFactory(
            partner=self.partner2,
            status=Application.SENT,
            editor=self.user.editor,
            sent_by=self.coordinator,
        )

        # Clear mail outbox since approvals send emails
        mail.outbox = []
        # Coordinator only wants reminders for apps under discussion
        self.coordinator.userprofile.pending_app_reminders = True
        self.coordinator.userprofile.approved_app_reminders = True
        self.coordinator.userprofile.save()

        call_command("send_coordinator_reminders")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("1 pending application", mail.outbox[0].body)
        self.assertIn("1 under discussion application", mail.outbox[0].body)
        self.assertIn("1 approved application", mail.outbox[0].body)


class SurveyActiveUsersEmailTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Creates a survey-eligible user and several eligible users.
        Returns
        -------
        None
        """

        now = timezone.now()

        eligible = EditorFactory(user__email="editor@example.com")
        eligible.wp_not_blocked = True
        eligible.wp_bundle_eligible = True
        eligible.wp_account_old_enough = True
        eligible.wp_registered = now - timedelta(days=182)
        eligible.wp_enough_edits = True
        eligible.user.userprofile.terms_of_use = True
        eligible.user.userprofile.save()
        eligible.user.last_login = now
        eligible.user.save()
        eligible.save()
        cls.eligible = eligible.user

        blocked = EditorFactory(user__email="blocked@example.com")
        blocked.wp_not_blocked = False
        blocked.wp_bundle_eligible = True
        blocked.wp_account_old_enough = True
        blocked.wp_registered = now - timedelta(days=182)
        blocked.wp_enough_edits = True
        blocked.user.userprofile.terms_of_use = True
        blocked.user.userprofile.save()
        blocked.user.last_login = now
        blocked.user.save()
        blocked.save()

        already_sent = EditorFactory(user__email="alreadysent@example.com")
        already_sent.wp_not_blocked = True
        already_sent.wp_bundle_eligible = True
        already_sent.wp_account_old_enough = True
        already_sent.wp_registered = now - timedelta(days=182)
        already_sent.wp_enough_edits = True
        already_sent.user.userprofile.terms_of_use = True
        already_sent.user.userprofile.survey_email_sent = True
        already_sent.user.userprofile.save()
        already_sent.user.last_login = now
        already_sent.user.save()
        already_sent.save()

        wmf_email = EditorFactory(user__email="editor@wikimedia.org")
        wmf_email.wp_not_blocked = True
        wmf_email.wp_bundle_eligible = True
        wmf_email.wp_account_old_enough = True
        wmf_email.wp_registered = now - timedelta(days=182)
        wmf_email.wp_enough_edits = True
        wmf_email.user.userprofile.terms_of_use = True
        wmf_email.user.userprofile.save()
        wmf_email.user.last_login = now
        wmf_email.user.save()
        wmf_email.save()

        too_new_at_login = EditorFactory(user__email="toonew@example.com")
        too_new_at_login.wp_not_blocked = True
        too_new_at_login.wp_bundle_eligible = True
        too_new_at_login.wp_account_old_enough = True
        too_new_at_login.wp_registered = now - timedelta(days=182)
        too_new_at_login.wp_enough_edits = True
        too_new_at_login.user.userprofile.terms_of_use = True
        too_new_at_login.user.userprofile.save()
        too_new_at_login.user.last_login = now - timedelta(days=30)
        too_new_at_login.user.save()
        too_new_at_login.save()

        not_enough_edits = EditorFactory(user__email="notenoughedits@example.com")
        not_enough_edits.wp_not_blocked = True
        not_enough_edits.wp_bundle_eligible = True
        not_enough_edits.wp_account_old_enough = True
        not_enough_edits.wp_registered = now - timedelta(days=182)
        not_enough_edits.wp_enough_edits = False
        not_enough_edits.user.userprofile.terms_of_use = True
        not_enough_edits.user.userprofile.save()
        not_enough_edits.user.last_login = now
        not_enough_edits.user.save()
        not_enough_edits.save()

        inactive = EditorFactory(user__email="inactive@example.com")
        inactive.wp_not_blocked = True
        inactive.wp_bundle_eligible = True
        inactive.wp_account_old_enough = True
        inactive.wp_registered = now - timedelta(days=182)
        inactive.wp_enough_edits = True
        inactive.user.userprofile.terms_of_use = True
        inactive.user.userprofile.save()
        inactive.user.last_login = now
        inactive.user.is_active = False
        inactive.user.save()
        inactive.save()

        staff = EditorFactory(user__email="staff@example.com")
        staff.wp_not_blocked = True
        staff.wp_bundle_eligible = True
        staff.wp_account_old_enough = True
        staff.wp_registered = now - timedelta(days=182)
        staff.wp_enough_edits = True
        staff.user.userprofile.terms_of_use = True
        staff.user.userprofile.save()
        staff.user.last_login = now
        staff.user.is_staff = True
        staff.user.save()
        staff.save()

        superuser = EditorFactory(user__email="superuser@example.com")
        superuser.wp_not_blocked = True
        superuser.wp_bundle_eligible = True
        superuser.wp_account_old_enough = True
        superuser.wp_registered = now - timedelta(days=182)
        superuser.wp_enough_edits = True
        superuser.user.userprofile.terms_of_use = True
        superuser.user.userprofile.save()
        superuser.user.last_login = now
        superuser.user.is_superuser = True
        superuser.user.save()
        superuser.save()

    # Use the same override as djmail itself since the command dynamically changes the backend
    @override_settings(
        DJMAIL_REAL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_survey_active_users_command(self):
        call_command(
            "survey_active_users",
            "000001",
            "en",
            backend="djmail.backends.default.EmailBackend",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.eligible.email])
