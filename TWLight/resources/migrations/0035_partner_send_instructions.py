# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0034_auto_20170624_1554'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='send_instructions',
            field=models.TextField(help_text='Optional instructions for sending application data to this partner.', null=True, blank=True),
        ),
    ]
