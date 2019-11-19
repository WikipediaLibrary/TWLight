# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_auto_20160511_1454"),
        ("applications", "0006_application_days_open"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="editor",
            field=models.ForeignKey(
                related_name="applications", blank=True, to="users.Editor", null=True
            ),
            preserve_default=True,
        )
    ]
