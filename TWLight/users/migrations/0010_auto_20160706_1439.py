# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import models, migrations


def create_profiles(apps, schema_editor):
    """
    Make sure that any already-created users have profiles, as the profile
    creation signal handler will never be triggered for already-existing users.
    """
    User = apps.get_model(settings.AUTH_USER_MODEL)
    UserProfile = apps.get_model("users", "UserProfile")

    for user in User.objects.all():
        profile = UserProfile()
        profile.user = user
        profile.terms_of_use = False  # Default value, but we're being explicit
        profile.save()


class Migration(migrations.Migration):

    dependencies = [("users", "0009_userprofile")]

    operations = [migrations.RunPython(create_profiles)]
