# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0041_partner_company_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partner',
            name='company_location',
            field=django_countries.fields.CountryField(help_text="Partner's primary location (e.g. 'United Kingdom').", max_length=2, null=True),
        ),
    ]
