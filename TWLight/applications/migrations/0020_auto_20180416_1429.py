# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0019_application_account_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='account_email',
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
    ]
