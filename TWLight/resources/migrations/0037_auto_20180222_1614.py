# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0036_auto_20170716_1235")]

    operations = [
        migrations.CreateModel(
            name="PartnerLogo",
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
                    "logo",
                    models.ImageField(
                        help_text="Optional image file that can be used to represent this partner.",
                        null=True,
                        upload_to=b"",
                        blank=True,
                    ),
                ),
            ],
        ),
        migrations.RemoveField(model_name="partner", name="logo_url"),
        migrations.AddField(
            model_name="partnerlogo",
            name="partner",
            field=models.OneToOneField(related_name="logos", to="resources.Partner"),
        ),
    ]
