# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0023_auto_20170820_1623")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="lang",
            field=models.CharField(
                blank=True,
                max_length=128,
                null=True,
                help_text="Language",
                choices=[(b"en", "English"), (b"fi", "Finnish"), (b"fr", "French")],
            ),
        )
    ]
