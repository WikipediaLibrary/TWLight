# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0003_partner_access_grant_term'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partner',
            name='access_grant_term',
            field=models.DurationField(help_text=b"The standard length of an access grant from this Partner. Enter like '365 days' or '365d' or '1 year'.", null=True, blank=True),
            preserve_default=True,
        ),
    ]
