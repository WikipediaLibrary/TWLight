# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-05-08 18:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0050_auto_20200109_1642")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="proxy_notification_sent",
            field=models.BooleanField(default=False),
        )
    ]
