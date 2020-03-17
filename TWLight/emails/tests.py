from datetime import datetime, timedelta

from djmail.template_mail import MagicMailBuilder, InlineCSSTemplateMail
from unittest.mock import patch

from django_comments import get_form_target
from django_comments.models import Comment
from django_comments.signals import comment_was_posted
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory

from TWLight.applications.factories import ApplicationFactory
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
    contact_us_emails,
)


class ApplicationCommentTest(TestCase):
    def setUp(self):
        super(ApplicationCommentTest, self).setUp()
        self.editor = EditorFactory(user__email="editor@example.com").user

        coordinators = get_coordinators()

        self.coordinator1 = EditorFactory(
            user__email="c1@example.com", user__username="c1"
        ).user
        self.coordinator2 = EditorFactory(
            user__email="c2@example.com", user__username="c2"
        ).user
        coordinators.user_set.add(self.coordinator1)
        coordinators.user_set.add(self.coordinator2)

        self.partner = PartnerFactory()

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

    # We'd like to mock out send_comment_notification_emails and test that
    # it is called when comment_was_posted is fired, but we can't; the signal
    # handler is attached to the real send_comment_notification_emails, not
    # the mocked one.


class ApplicationStatusTest(TestCase):
    @patch("TWLight.emails.tasks.send_approval_notification_email")
    def test_approval_calls_email_function(self, mock_email):
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.APPROVED
        app.save()
        self.assertTrue(mock_email.called)

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
        _ = ApplicationFactory(status=Application.SENT)
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
        app = ApplicationFactory(status=Application.SENT, partner=partner)
        self.assertFalse(mock_email.called)

        partner.status = Partner.WAITLIST
        partner.save()
        self.assertFalse(mock_email.called)


class ContactUsTest(TestCase):
    def setUp(self):
        super(ContactUsTest, self).setUp()
        self.editor = EditorFactory(user__email="editor@example.com").user

    @patch("TWLight.emails.tasks.contact_us_emails")
    def test_contact_us_emails(self, mock_email):
        factory = RequestFactory()
        request = factory.post(get_form_target())
        request.user = UserFactory()
        editor = EditorFactory()
        reply_to = ["editor@example.com"]
        cc = ["editor@example.com"]

        self.assertEqual(len(mail.outbox), 0)

        mail_instance = MagicMailBuilder(template_mail_cls=InlineCSSTemplateMail)
        email = mail_instance.contact_us_email(
            "wikipedialibrary@wikimedia.org",
            {"editor_wp_username": editor.wp_username, "body": "This is a test email"},
        )
        email.extra_headers["Reply-To"] = ", ".join(reply_to)
        email.extra_headers["Cc"] = ", ".join(cc)
        email.send()

        self.assertEqual(len(mail.outbox), 1)

    def test_user_submit_contact_us_emails(self):
        EditorCraftRoom(self, Terms=True, Coordinator=False)

        self.assertEqual(len(mail.outbox), 0)

        contact_us_url = reverse("contact")
        contact_us = self.client.get(contact_us_url, follow=True)
        contact_us_form = contact_us.context["form"]
        data = contact_us_form.initial
        data["email"] = "editor@example.com"
        data["message"] = "This is a test"
        data["cc"] = True
        data["submit"] = True
        self.client.post(contact_us_url, data)

        self.assertEqual(len(mail.outbox), 1)

    def test_not_logged_in_user_submit_contact_us_emails(self):
        self.assertEqual(len(mail.outbox), 0)

        contact_us_url = reverse("contact")
        contact_us = self.client.get(contact_us_url, follow=True)
        contact_us_form = contact_us.context["form"]
        data = contact_us_form.initial
        data["email"] = "editor@example.com"
        data["message"] = "This is a test"
        data["submit"] = True
        data["cc"] = True
        self.client.post(contact_us_url, data)

        self.assertEqual(len(mail.outbox), 0)


class UserRenewalNoticeTest(TestCase):
    def setUp(self):
        super(UserRenewalNoticeTest, self).setUp()
        editor = EditorFactory(user__email="editor@example.com")
        self.user = editor.user

        self.coordinator = EditorFactory().user
        coordinators = get_coordinators()
        coordinators.user_set.add(self.coordinator)

        self.partner = PartnerFactory()

        self.authorization = Authorization()
        self.authorization.user = self.user
        self.authorization.authorizer = self.coordinator
        self.authorization.date_expires = datetime.today() + timedelta(weeks=2)
        self.authorization.save()
        self.authorization.partners.add(self.partner)

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
        authorization2.partner = self.partner
        authorization2.date_expires = datetime.today() + timedelta(weeks=1)
        authorization2.save()

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


class CoordinatorReminderEmailTest(TestCase):
    def setUp(self):
        super(CoordinatorReminderEmailTest, self).setUp()
        editor = EditorFactory()
        self.user = editor.user
        editor2 = EditorFactory()
        self.user2 = editor2.user

        self.coordinator = EditorFactory(user__email="editor@example.com").user
        coordinators = get_coordinators()
        coordinators.user_set.add(self.coordinator)

        self.partner = PartnerFactory(coordinator=self.coordinator)
        self.partner2 = PartnerFactory(coordinator=self.coordinator)

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
        self.assertNotIn("One pending application", mail.outbox[0].body)
        self.assertIn("One under discussion application", mail.outbox[0].body)
        self.assertNotIn("One approved application", mail.outbox[0].body)

        ApplicationFactory(
            partner=self.partner, status=Application.APPROVED, editor=self.user2.editor
        )
        ApplicationFactory(
            partner=self.partner2, status=Application.SENT, editor=self.user.editor
        )

        # Clear mail outbox since approvals send emails
        mail.outbox = []
        # Coordinator only wants reminders for apps under discussion
        self.coordinator.userprofile.pending_app_reminders = True
        self.coordinator.userprofile.approved_app_reminders = True
        self.coordinator.userprofile.save()

        call_command("send_coordinator_reminders")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("One pending application", mail.outbox[0].body)
        self.assertIn("One under discussion application", mail.outbox[0].body)
        self.assertIn("One approved application", mail.outbox[0].body)
