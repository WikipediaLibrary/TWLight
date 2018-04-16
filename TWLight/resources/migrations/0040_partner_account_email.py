# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0039_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='account_email',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to have already signed up at the partner website.'),
        ),
    ]
