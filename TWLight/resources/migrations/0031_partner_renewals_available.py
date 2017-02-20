# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0030_auto_20170203_1620'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='renewals_available',
            field=models.BooleanField(default=False, help_text='Can access grants to this partner be renewed? If so, users will be able to request renewals when their access is close to expiring.'),
        ),
    ]
