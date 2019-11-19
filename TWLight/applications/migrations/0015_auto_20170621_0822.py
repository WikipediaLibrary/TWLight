# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("applications", "0014_application_parent")]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="date_closed",
            field=models.DateField(
                help_text="Please do not override this field! Its value is set automatically.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="days_open",
            field=models.IntegerField(
                help_text="Please do not override this field! Its value is set automatically.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="earliest_expiry_date",
            field=models.DateField(
                help_text="Please do not override this field! Its value is set automatically.",
                null=True,
                blank=True,
            ),
        ),
    ]
