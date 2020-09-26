# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-01 11:37


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0024_userprofile_lang")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="data_restricted",
            field=models.BooleanField(
                default=False,
                help_text="Has this user requested a restriction on the processing of their data?",
            ),
        )
    ]
