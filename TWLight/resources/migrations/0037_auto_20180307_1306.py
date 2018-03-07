# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0036_auto_20170716_1235'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='already_signed_up',
            field=models.BooleanField(default=False, help_text="Mark as true if this partner requires applicants to sign up on the partner's website before applying."),
        ),
        migrations.AddField(
            model_name='partner',
            name='sign_up_link',
            field=models.URLField(help_text='Link to signup page. Required if users must register an account before applying for access; optional otherwise.', null=True, blank=True),
        ),
    ]
