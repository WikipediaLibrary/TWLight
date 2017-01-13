from mock import patch

from django_comments import get_form_target
from django_comments.models import Comment
from django_comments.signals import comment_was_posted
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase, RequestFactory

from TWLight.applications.factories import ApplicationFactory
from TWLight.applications.models import Application
from TWLight.users.factories import EditorFactory
from TWLight.users.groups import get_coordinators

# We need to import these in order to register the signal handlers; if we don't,
# when we test that those handler functions have been called, we will get
# False even when they work in real life.
from .tasks import (send_comment_notification_emails,
                    send_approval_notification_email,
                    send_rejection_notification_email)

class ApplicationCommentTest(TestCase):

    def setUp(self):
        super(ApplicationCommentTest, self).setUp()
        self.editor = EditorFactory(user__email='editor@example.com').user

        coordinators = get_coordinators()

        self.coordinator1 = EditorFactory(user__email='c1@example.com',
                                          user__username='c1').user
        self.coordinator2 = EditorFactory(user__email='c2@example.com',
                                          user__username='c2').user
        coordinators.user_set.add(self.coordinator1)
        coordinators.user_set.add(self.coordinator2)


    def _create_comment(self, app, user):
        CT = ContentType.objects.get_for_model

        comm = Comment.objects.create(
            content_type=CT(Application),
            object_pk=app.pk,
            user=user,
            user_name=user.username,
            user_email=user.email,
            comment="Content!",
            site=Site.objects.get_current(),
        )
        comm.save()

        return comm

    def _set_up_email_test_objects(self):
        app = ApplicationFactory(editor=self.editor.editor)

        factory = RequestFactory()
        request = factory.post(get_form_target())
        return app, request

    def test_comment_email_sending_1(self):
        """
        A coordinator posts a comment to an Editor's application and an email
        is send to that Editor. An email is not sent to the coordinator.
        """
        app, request = self._set_up_email_test_objects()

        self.assertEqual(len(mail.outbox), 0)

        comment1 = self._create_comment(app, self.coordinator1)
        comment_was_posted.send(
            sender=Comment,
            comment=comment1,
            request=request
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.editor.email])


    def test_comment_email_sending_2(self):
        """
        After a coordinator posts a comment, the Editor posts an additional
        comment. An email is sent to the coordinator who posted the earlier
        comment. An email is not sent to the editor.
        """
        app, request = self._set_up_email_test_objects()
        self.assertEqual(len(mail.outbox), 0)

        _ = self._create_comment(app, self.coordinator1)
        comment2 = self._create_comment(app, self.editor)

        comment_was_posted.send(
            sender=Comment,
            comment=comment2,
            request=request
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.coordinator1.email])


    def test_comment_email_sending_3(self):
        """
        After the editor and coordinator post a comment, an additional
        coordinator posts a comment. One email is sent to the first coordinator,
        and a distinct email is sent to the editor.
        """
        app, request = self._set_up_email_test_objects()
        self.assertEqual(len(mail.outbox), 0)

        _ = self._create_comment(app, self.coordinator1)
        _ = self._create_comment(app, self.editor)
        comment3 = self._create_comment(app, self.coordinator2)
        comment_was_posted.send(
            sender=Comment,
            comment=comment3,
            request=request
            )

        self.assertEqual(len(mail.outbox), 2)

        # Either order of email sending is fine.
        try:
            self.assertEqual(mail.outbox[0].to, [self.coordinator1.email])
            self.assertEqual(mail.outbox[1].to, [self.editor.email])
        except AssertionError:
            self.assertEqual(mail.outbox[1].to, [self.coordinator1.email])
            self.assertEqual(mail.outbox[0].to, [self.editor.email])


    @patch('TWLight.emails.tasks.send_comment_notification_emails')
    def test_commenting_calls_email_function(self, mock_email):
        app, request = self._set_up_email_test_objects()

        self.assertEqual(len(mail.outbox), 0)

        comment1 = self._create_comment(app, self.coordinator1)
        comment_was_posted.send(
            sender=Comment,
            comment=comment1,
            request=request
            )

        self.assertTrue(mock_email.called)



class ApplicationStatusTest(TestCase):
    @patch('TWLight.emails.tasks.send_approval_notification_email')
    def test_approval_calls_email_function(self, mock_email):
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.APPROVED
        app.save()
        self.assertTrue(mock_email.called)


    @patch('TWLight.emails.tasks.send_rejection_notification_email')
    def test_rejection_calls_email_function(self, mock_email):
        app = ApplicationFactory(status=Application.PENDING)
        app.status = Application.NOT_APPROVED
        app.save()
        self.assertTrue(mock_email.called)


    # Application.WAITLIST is not yet implemented.
    # def test_waitlisting_calls_email_function(self):
    #     assert False
