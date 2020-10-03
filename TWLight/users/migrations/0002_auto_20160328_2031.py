# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("users", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="editor",
            name="affiliation",
            field=models.CharField(max_length=128, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="editor",
            name="country_of_residence",
            field=models.CharField(max_length=128, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="editor",
            name="occupation",
            field=models.CharField(max_length=128, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="editor",
            name="real_name",
            field=models.CharField(max_length=128, blank=True),
            preserve_default=True,
        ),
    ]
