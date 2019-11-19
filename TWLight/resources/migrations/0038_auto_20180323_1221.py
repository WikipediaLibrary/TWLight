# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0037_auto_20180222_1614")]

    operations = [
        migrations.RemoveField(model_name="partner", name="access_grant_term"),
        migrations.AlterField(
            model_name="partner",
            name="renewals_available",
            field=models.BooleanField(
                default=False,
                help_text="Can access grants to this partner be renewed? If so, users will be able to request renewals at any time.",
            ),
        ),
    ]
