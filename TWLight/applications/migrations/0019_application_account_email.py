# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0018_remove_application_earliest_expiry_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='account_email',
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
    ]
