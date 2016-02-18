# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=30, help_text='Organizational role or job title. This is NOT intended to be used for honorofics.')),
                ('email', models.EmailField(max_length=254)),
                ('full_name', models.CharField(max_length=50)),
                ('short_name', models.CharField(max_length=15, help_text="The form of the contact person's name to use in email greetings (as in 'Hi Jake')")),
            ],
        ),
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('company_name', models.CharField(max_length=30, help_text="Partner organization's name (e.g. McFarland). Note: this will be user-visible and *not translated*.")),
                ('terms_of_use', models.URLField(null=True, blank=True, help_text='Required if this company requires that users agree to terms of use as a condition of applying for access; optional otherwise.')),
                ('description', models.TextField(blank=True, null=True, help_text="Optional description of this partner's offerings.")),
                ('mutually_exclusive', models.NullBooleanField(default=None, help_text='If True, users can only apply for one Stream at a time from this Partner. If False, users can apply for multiple Streams at a time. This field must be filled in when Partners have multiple Streams, but may be left blank otherwise.')),
                ('real_name', models.BooleanField(default=False)),
                ('country_of_residence', models.BooleanField(default=False)),
                ('specific_title', models.BooleanField(default=False)),
                ('specific_stream', models.BooleanField(default=False)),
                ('occupation', models.BooleanField(default=False)),
                ('affiliation', models.BooleanField(default=False)),
                ('agreement_with_terms_of_use', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50, help_text="Name of stream (e.g. 'Health and Behavioral Sciences.Will be user-visible and *not translated*. Do not include the name of the partner here. If partner name and resource name need to be presented together, templates are responsible for presenting them in a format that can be internationalized.")),
                ('description', models.TextField(blank=True, null=True, help_text="Optional description of this stream's contents.")),
                ('partner', models.ForeignKey(related_name='streams', to='resources.Partner')),
            ],
        ),
        migrations.AddField(
            model_name='contact',
            name='partner',
            field=models.ForeignKey(related_name='contacts', to='resources.Partner'),
        ),
    ]
