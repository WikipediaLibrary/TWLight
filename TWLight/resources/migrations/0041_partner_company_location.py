# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0040_partner_featured'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='company_location',
            field=models.CharField(help_text="Partner's primary location (e.g. 'United Kingdom'.", max_length=50, null=True, blank=True),
        ),
    ]
