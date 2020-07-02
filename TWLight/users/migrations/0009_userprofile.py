# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0008_auto_20160706_1409"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("terms_of_use", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(
                        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE
                    ),
                ),
            ],
            options={
                "verbose_name": "user profile",
                "verbose_name_plural": "user profiles",
            },
            bases=(models.Model,),
        )
    ]
