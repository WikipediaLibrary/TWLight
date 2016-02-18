# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('rationale', models.TextField(blank=True)),
                ('title_requested', models.CharField(max_length=128, blank=True)),
                ('stream_requested', models.CharField(max_length=128, blank=True)),
                ('comments', models.TextField(blank=True)),
                ('agreement_with_terms', models.BooleanField(default=False)),
                ('partners', models.ForeignKey(to='resources.Partner')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
