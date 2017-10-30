# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone


def copy_editor_data(apps, schema_editor):
    Application = apps.get_model("applications", "Application")
    for app in Application.objects.all():
        if hasattr(app.user, 'editor'):
            app.editor = app.user.editor
            app.save()
        else:
            app.delete()


class Migration(migrations.Migration):

    replaces = [(b'applications', '0001_initial'), (b'applications', '0002_application_date_created'), (b'applications', '0003_application_date_closed'), (b'applications', '0004_auto_20160427_2120'), (b'applications', '0005_application_earliest_expiry_date'), (b'applications', '0006_application_days_open'), (b'applications', '0007_application_editor'), (b'applications', '0008_auto_20160527_1502'), (b'applications', '0009_auto_20160527_1505'), (b'applications', '0010_auto_20160706_1409'), (b'applications', '0011_auto_20160908_1410'), (b'applications', '0012_auto_20160930_1434'), (b'applications', '0013_application_sent_by'), (b'applications', '0014_application_parent'), (b'applications', '0015_auto_20170621_0822'), (b'applications', '0016_auto_20170707_1552'), (b'applications', '0017_auto_20170709_1859')]

    dependencies = [
        ('resources', '0002_auto_20160324_1826'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0007_auto_20160511_1454'),
    ]

    operations = [
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(default=0, choices=[(0, 'Pending'), (1, 'Under discussion'), (2, 'Approved'), (3, 'Not approved')])),
                ('rationale', models.TextField(blank=True)),
                ('specific_title', models.CharField(max_length=128, blank=True)),
                ('comments', models.TextField(blank=True)),
                ('agreement_with_terms_of_use', models.BooleanField(default=False)),
                ('partner', models.ForeignKey(related_name='applications', to='resources.Partner')),
                ('specific_stream', models.ForeignKey(related_name='applications', blank=True, to='resources.Stream', null=True)),
                ('user', models.ForeignKey(related_name='applications', to=settings.AUTH_USER_MODEL)),
                ('date_created', models.DateField(default=datetime.datetime(2016, 4, 26, 15, 54, 22, 38710, tzinfo=utc), auto_now_add=True)),
                ('date_closed', models.DateField(help_text='Please do not override this field! It is set automatically.', null=True, blank=True)),
                ('earliest_expiry_date', models.DateField(help_text='Please do not override this field! It is set automatically.', null=True, blank=True)),
                ('days_open', models.IntegerField(help_text='Please do not override this field! It is set automatically.', null=True, blank=True)),
                ('editor', models.ForeignKey(related_name='applications', blank=True, to='users.Editor', null=True)),
            ],
        ),
        migrations.RunPython(
            code=copy_editor_data,
        ),
        migrations.RemoveField(
            model_name='application',
            name='user',
        ),
        migrations.AlterField(
            model_name='application',
            name='editor',
            field=models.ForeignKey(related_name='applications', default=1, to='users.Editor'),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='application',
            options={'verbose_name': 'application', 'verbose_name_plural': 'applications'},
        ),
        migrations.AlterModelOptions(
            name='application',
            options={'ordering': ['-date_created', 'editor', 'partner'], 'verbose_name': 'application', 'verbose_name_plural': 'applications'},
        ),
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, 'Pending'), (1, 'Under discussion'), (2, 'Approved'), (3, 'Not approved'), (4, 'Sent to partner')]),
        ),
        migrations.AddField(
            model_name='application',
            name='sent_by',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The user who sent this application to the partner', null=True),
        ),
        migrations.AddField(
            model_name='application',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='applications.Application', null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='date_closed',
            field=models.DateField(help_text='Please do not override this field! Its value is set automatically.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='days_open',
            field=models.IntegerField(help_text='Please do not override this field! Its value is set automatically.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='earliest_expiry_date',
            field=models.DateField(help_text='Please do not override this field! Its value is set automatically.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='date_created',
            field=models.DateField(default=django.utils.timezone.now, editable=False, blank=True),
        ),
        migrations.AddField(
            model_name='application',
            name='imported',
            field=models.NullBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='application',
            name='date_created',
            field=models.DateField(default=django.utils.timezone.now, editable=False),
        ),
    ]
