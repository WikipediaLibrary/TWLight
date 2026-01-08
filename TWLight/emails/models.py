# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext as _, override

from djmail.models import Message

from TWLight.users.models import UserProfile


class MessageQuerySet(models.QuerySet):
    def unsent(self):
        return self.exclude(status=Message.STATUS_SENT)

    def users_with_unsent(self):
        email_addresses = self.unsent().values_list("to_email", flat=True)
        return User.objects.filter(email__in=email_addresses)

    def userprofiles_with_unsent(self):
        email_addresses = self.unsent().values_list("to_email", flat=True)
        return UserProfile.objects.select_related("user").filter(
            user__email__in=email_addresses
        )

    def user_pks_with_subject_list(self, subject, users):
        user_pks = []
        if users is None:
            return user_pks

        subjects = []
        # Get the localized subject for each specified language
        for lang_code, _lang_name in settings.LANGUAGES:
            try:
                with override(lang_code):
                    # Translators: do not translate
                    subjects.append(_(subject))
            except ValueError:
                pass

        # Since the message object contains translated text, search for the localized email subject to check for existing messages.
        for user in users.only("pk", "email"):
            # search for Message objects with matching subject and recipient
            existing_messages = self.filter(
                to_email=user.email,
                subject__in=subjects,
            )
            if existing_messages.exists():
                user_pks.append(user.pk)
        return user_pks


class MessageManager(models.Manager):
    def get_queryset(self):
        return MessageQuerySet(self.model, using=self._db)

    def unsent(self):
        return self.get_queryset().unsent()

    def userprofiles_with_unsent(self):
        return self.get_queryset().userprofiles_with_unsent()

    def user_pks_with_subject_list(self, subject, users):
        return self.get_queryset().user_pks_with_subject_list(
            subject=subject, users=users
        )


# add "twl" manager to Message
Message.add_to_class("twl", MessageManager())
