# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('applications', '0012_auto_20160930_1434'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='sent_by',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The user who sent this application to the partner', null=True),
            preserve_default=True,
        ),
    ]
