# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0037_auto_20180222_1614")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="bundle",
            field=models.BooleanField(
                default=False,
                null=True,
                help_text="Is this partner a part of the Bundle?",
            ),
        )
    ]
