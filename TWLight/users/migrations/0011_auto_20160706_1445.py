# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("users", "0010_auto_20160706_1439")]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="terms_of_use",
            field=models.BooleanField(
                default=False, help_text="Has this user agreed with the terms of use?"
            ),
            preserve_default=True,
        )
    ]
