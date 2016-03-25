# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resources', '0002_auto_20160324_1826'),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rationale', models.TextField(blank=True)),
                ('title_requested', models.CharField(max_length=128, blank=True)),
                ('stream_requested', models.CharField(max_length=128, blank=True)),
                ('comments', models.TextField(blank=True)),
                ('agreement_with_terms', models.BooleanField(default=False)),
                ('partner', models.ForeignKey(to='resources.Partner')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
