# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models

from djmail.models import Message


from TWLight.users.models import UserProfile


class MessageManager(models.Manager):
    def drafts(self, subject=None):
        if subject is not None:
            return self.filter(status=Message.STATUS_DRAFT, subject=subject)
        return self.filter(status=Message.STATUS_DRAFT)

    def users_with_drafts(self, subject=None):
        email_addresses = self.drafts(subject).values_list("to_email", flat=True)

        return User.objects.select_related("userprofile").filter(
            email__in=email_addresses
        )

    def userprofiles_with_drafts(self, subject=None):
        email_addresses = self.drafts(subject).values_list("to_email", flat=True)

        return UserProfile.objects.select_related("user").filter(
            user__email__in=email_addresses
        )

    def bulk_cleanup_drafts(self, subject=None, userprofile_flag_field=None):
        if subject is not None and userprofile_flag_field is not None:
            userprofiles = self.userprofiles_with_drafts(subject=subject).filter(
                **{userprofile_flag_field: True}
            )
            for userprofile in userprofiles:
                setattr(userprofile, userprofile_flag_field, False)
            UserProfile.objects.bulk_update(
                userprofiles, [userprofile_flag_field], batch_size=1000
            )

        if subject is not None:
            self.drafts(subject=subject).delete()


Message.add_to_class("objects", MessageManager())
