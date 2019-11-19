# -*- coding: utf-8 -*-


from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("resources", "0025_auto_20170113_1614"),
    ]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="coordinator",
            field=models.ForeignKey(
                blank=True,
                to=settings.AUTH_USER_MODEL,
                help_text="The coordinator for this Partner, if any.",
                null=True,
            ),
        )
    ]
