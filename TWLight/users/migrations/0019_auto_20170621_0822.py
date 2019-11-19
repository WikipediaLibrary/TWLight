# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0018_auto_20170611_1344")]

    operations = [
        migrations.AlterField(
            model_name="editor",
            name="wp_valid",
            field=models.BooleanField(
                default=False,
                help_text="At their last login, did this user meet the criteria in the terms of use?",
            ),
        )
    ]
