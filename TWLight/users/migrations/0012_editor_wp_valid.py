# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("users", "0011_auto_20160706_1445")]

    operations = [
        migrations.AddField(
            model_name="editor",
            name="wp_valid",
            field=models.BooleanField(
                default=False,
                help_text="At their last login, did this user meet the criteria set forth in the Wikipedia Library Card Platform terms of use?",
            ),
            preserve_default=True,
        )
    ]
