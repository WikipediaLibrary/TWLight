# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("users", "0005_auto_20160408_1722")]

    operations = [
        migrations.RemoveField(model_name="editor", name="_wp_internal"),
        migrations.AddField(
            model_name="editor",
            name="wp_groups",
            field=models.TextField(default="a group", help_text="Wikipedia groups"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="editor",
            name="wp_rights",
            field=models.TextField(
                default="a right", help_text="Wikipedia user rights"
            ),
            preserve_default=False,
        ),
    ]
