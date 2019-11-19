# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0021_auto_20170709_1859")]

    operations = [
        migrations.AlterField(
            model_name="editor",
            name="wp_groups",
            field=models.TextField(help_text="Wikipedia groups", blank=True),
        ),
        migrations.AlterField(
            model_name="editor",
            name="wp_rights",
            field=models.TextField(help_text="Wikipedia user rights", blank=True),
        ),
    ]
