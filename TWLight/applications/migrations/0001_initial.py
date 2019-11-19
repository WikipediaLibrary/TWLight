# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0002_auto_20160324_1826"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Application",
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
                (
                    "status",
                    models.IntegerField(
                        default=0,
                        choices=[
                            (0, "Pending"),
                            (1, "Under discussion"),
                            (2, "Approved"),
                            (3, "Not approved"),
                        ],
                    ),
                ),
                ("rationale", models.TextField(blank=True)),
                ("specific_title", models.CharField(max_length=128, blank=True)),
                ("comments", models.TextField(blank=True)),
                ("agreement_with_terms_of_use", models.BooleanField(default=False)),
                (
                    "partner",
                    models.ForeignKey(
                        related_name="applications", to="resources.Partner"
                    ),
                ),
                (
                    "specific_stream",
                    models.ForeignKey(
                        related_name="applications",
                        blank=True,
                        to="resources.Stream",
                        null=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        related_name="applications", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
