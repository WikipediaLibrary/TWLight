# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0032_auto_20170611_1344")]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="company_name",
            field=models.CharField(
                help_text="Partner's name (e.g. McFarland). Note: this will be user-visible and *not translated*.",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="country_of_residence",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicant countries of residence.",
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description",
            field=models.TextField(
                help_text="Optional description of this partner's resources.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_en",
            field=models.TextField(
                help_text="Optional description of this partner's resources.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_fi",
            field=models.TextField(
                help_text="Optional description of this partner's resources.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_fr",
            field=models.TextField(
                help_text="Optional description of this partner's resources.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="real_name",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicant names.",
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="specific_stream",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify the database they want to access.",
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="specific_title",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify the title they want to access.",
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="terms_of_use",
            field=models.URLField(
                help_text="Link to terms of use. Required if users must agree to terms of use to get access; optional otherwise.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="stream",
            name="description",
            field=models.TextField(
                help_text="Optional description of this stream's resources.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="stream",
            name="name",
            field=models.CharField(
                help_text="Name of stream (e.g. 'Health and Behavioral Sciences). Will be user-visible and *not translated*. Do not include the name of the partner here.",
                max_length=50,
            ),
        ),
    ]
