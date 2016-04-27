# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import json

from django.core.mail import EmailMessage
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

from . import core
from . import models
from . import utils
from .template_mail import TemplateMail
from .template_mail import MagicMailBuilder
from .template_mail import make_email


class EmailTestCaseMixin(object):
    def setUp(self):
        models.Message.objects.all().delete()
        self.email = EmailMessage('Hello', 'Body goes here', 'from@example.com',
                                  ['to1@example.com', 'to2@example.com'])

    def assertEmailEqual(self, a, b):
        # Can't do simple equality comparison... That sucks!
        self.assertEqual(a.__class__, b.__class__)
        self.assertEqual(a.__dict__, b.__dict__)
        self.assertEqual(dir(a), dir(b))


class TestEmailSending(EmailTestCaseMixin, TestCase):
    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_simple_send_email(self):
        self.email.send()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.async.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DJMAIL_SEND_ASYNC=True)
    def test_async_send_email(self):
        # If async is activated, send method returns a thread instead of
        # a number of sent messages.
        future = self.email.send()
        future.result()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='testing.mocks.BrokenEmailBackend')
    def test_failing_simple_send_email(self):
        number_sent_emails = self.email.send()

        self.assertEqual(number_sent_emails, 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(models.Message.objects.count(), 1)
        self.assertEqual(models.Message.objects.get().status, models.STATUS_FAILED)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.async.EmailBackend',
        DJMAIL_REAL_BACKEND='testing.mocks.BrokenEmailBackend')
    def test_failing_async_send_email(self):
        future = self.email.send()
        future.result()

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(models.Message.objects.count(), 1)
        self.assertEqual(models.Message.objects.get().status, models.STATUS_FAILED)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.celery.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_async_send_email_with_celery(self):
        result = self.email.send()
        result.wait()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.celery.EmailBackend',
        DJMAIL_REAL_BACKEND='testing.mocks.BrokenEmailBackend')
    def test_failing_async_send_email_with_celery(self):
        result = self.email.send()
        result.wait()

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(models.Message.objects.count(), 1)
        self.assertEqual(models.Message.objects.get().status, models.STATUS_FAILED)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.celery.EmailBackend',
        DJMAIL_REAL_BACKEND='testing.mocks.BrokenEmailBackend')
    def test_failing_retry_send_01(self):
        message_model = models.Message.from_email_message(self.email)
        message_model.status = models.STATUS_FAILED
        message_model.retry_count = 1
        message_model.save()

        core._retry_send_messages()

        message_model_2 = models.Message.objects.get(pk=message_model.pk)
        self.assertEqual(message_model_2.retry_count, 2)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.celery.EmailBackend',
        DJMAIL_REAL_BACKEND='testing.mocks.BrokenEmailBackend',
        DJMAIL_MAX_RETRY_NUMBER=2)
    def test_failing_retry_send_02(self):
        message_model = models.Message.from_email_message(self.email)
        message_model.status = models.STATUS_FAILED
        message_model.retry_count = 3
        message_model.save()

        core._mark_discarded_messages()

        message_model_2 = models.Message.objects.get(pk=message_model.pk)
        self.assertEqual(message_model_2.retry_count, 3)
        self.assertEqual(message_model_2.status, models.STATUS_DISCARDED)


class TestTemplateEmailSending(EmailTestCaseMixin, TestCase):
    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_simple_send_email_1(self):
        class SimpleTemplateMail(TemplateMail):
            name = 'test_email1'

        email = SimpleTemplateMail()
        email.send('to@example.com', {'name': 'foo'})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

        m = mail.outbox[0]
        self.assertEqual(m.subject, u'Subject1: foo')
        self.assertEqual(m.body, u'<b>Mail1: foo</b>\n')

    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_simple_send_email_2(self):
        class SimpleTemplateMail(TemplateMail):
            name = 'test_email2'

        email = SimpleTemplateMail()
        email.send('to@example.com', {'name': 'foo'})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

        m = mail.outbox[0]
        self.assertEqual(m.subject, u'Subject2: foo')
        self.assertEqual(m.body, u'body\n')
        self.assertEqual(m.alternatives, [(u'<b>Body</b>\n', 'text/html')])

    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_simple_send_email_with_magic_builder_1(self):
        mails = MagicMailBuilder()

        email = mails.test_email2('to@example.com', {'name': 'foo'})
        email.send()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

        self.assertEqual(email.subject, u'Subject2: foo')
        self.assertEqual(email.body, u"body\n")
        self.assertEqual(email.alternatives, [(u'<b>Body</b>\n', 'text/html')])

    @override_settings(
        EMAIL_BACKEND="djmail.backends.default.EmailBackend",
        DJMAIL_REAL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_simple_send_email_with_magic_builder_1_with_extra_kwargs(self):
        mails = MagicMailBuilder()

        email = mails.test_email2("to@example.com",
                                  {"name": "foo"},
                                  from_email="no-reply@test.com")
        email.send()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

        self.assertEqual(email.subject, 'Subject2: foo')
        self.assertEqual(email.body, 'body\n')
        self.assertEqual(email.alternatives, [(u'<b>Body</b>\n', 'text/html')])

    def test_simple_email_building(self):
        email = make_email('test_email1',
                           to='to@example.com',
                           context={'name': 'foo'})

        self.assertEqual(email.subject, 'Subject1: foo')
        self.assertEqual(email.body, '<b>Mail1: foo</b>\n')

    def test_proper_handlign_different_uses_cases(self):
        from django.core import mail

        email1 = make_email('test_email1',
                            to='to@example.com',
                            context={'name': 'foo'})

        email2 = make_email('test_email2',
                            to='to@example.com',
                            context={'name': 'foo'})

        email3 = make_email('test_email3',
                            to='to@example.com',
                            context={'name': 'foo'})

        self.assertIsInstance(email1, mail.EmailMessage)
        self.assertEqual(email1.content_subtype, 'html')

        self.assertIsInstance(email2, mail.EmailMultiAlternatives)

        self.assertIsInstance(email3, mail.EmailMessage)
        self.assertEqual(email3.content_subtype, 'plain')

    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_simple_send_email_with_magic_builder_1_with_low_priority(self):
        mails = MagicMailBuilder()

        email = mails.test_email2('to@example.com', {'name': 'foo'}, priority=10)
        email.send()

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(models.Message.objects.count(), 1)

        m1 = models.Message.objects.get()
        self.assertEqual(m1.status, models.STATUS_PENDING)
        self.assertEqual(m1.priority, 10)

        core._send_pending_messages()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(models.Message.objects.count(), 1)

        m2 = models.Message.objects.get()
        self.assertEqual(m2.status, models.STATUS_SENT)
        self.assertEqual(m2.priority, 10)


class SerializationEmailTests(EmailTestCaseMixin, TestCase):
    def test_serialization_loop(self):
        data = utils.serialize_email_message(self.email)
        email_bis = utils.deserialize_email_message(data)
        self.assertEmailEqual(self.email, email_bis)

    def test_json_serialization_loop(self):
        with self.assertRaises(TypeError):
            json.dumps(self.email)
        json_data = json.dumps(utils.serialize_email_message(self.email))
        email_bis = utils.deserialize_email_message(json.loads(json_data))
        self.assertEmailEqual(self.email, email_bis)

    @override_settings(
        EMAIL_BACKEND='djmail.backends.default.EmailBackend',
        DJMAIL_REAL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_simple_send_email_with_magic_builder_1(self):
        mails = MagicMailBuilder()

        email = mails.test_email2('to@example.com', {'name': 'foo'})
        email.send()

        model = models.Message.objects.get()
        self.assertEqual(email.from_email, model.from_email)
        self.assertEqual(email.to, model.to_email.split(','))
        self.assertEqual(email.subject, model.subject)
        self.assertEqual(email.body, model.body_text)
