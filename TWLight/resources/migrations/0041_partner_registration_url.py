# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0040_partner_account_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='registration_url',
            field=models.URLField(help_text="Link to registration page. Required if users must sign up on the partner's website in advance; optional otherwise.", null=True, blank=True),
        ),
    ]
