# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0024_userprofile_lang")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="terms_of_use_date",
            field=models.DateField(
                help_text="The date this user agreed to the terms of use.",
                null=True,
                blank=True,
            ),
        )
    ]
