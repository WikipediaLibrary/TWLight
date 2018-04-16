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
            name='featured',
            field=models.BooleanField(default=False, help_text='Mark as true to feature this partner on the front page.'),
        ),
    ]
