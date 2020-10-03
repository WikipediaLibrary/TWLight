# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("applications", "0005_application_earliest_expiry_date")]

    operations = [
        migrations.AddField(
            model_name="application",
            name="days_open",
            field=models.IntegerField(
                help_text="Please do not override this field! It is set automatically.",
                null=True,
                blank=True,
            ),
            preserve_default=True,
        )
    ]
