# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-08 11:51


from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("users", "0025_userprofile_terms_of_use_date")]

    operations = [migrations.RemoveField(model_name="editor", name="last_updated")]
