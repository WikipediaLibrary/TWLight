# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('uuid', models.CharField(max_length=40, serialize=False, primary_key=True)),
                ('from_email', models.CharField(max_length=1024, blank=True)),
                ('to_email', models.TextField(blank=True)),
                ('body_text', models.TextField(blank=True)),
                ('body_html', models.TextField(blank=True)),
                ('subject', models.CharField(max_length=1024, blank=True)),
                ('data', models.TextField(editable=False, blank=True)),
                ('retry_count', models.SmallIntegerField(default=-1)),
                ('status', models.SmallIntegerField(default=10, choices=[(10, 'Draft'), (30, 'Sent'), (40, 'Failed'), (50, 'Discarded')])),
                ('priority', models.SmallIntegerField(default=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(default=None, null=True)),
                ('exception', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Message',
                'verbose_name_plural': 'Messages',
            },
            bases=(models.Model,),
        ),
    ]
