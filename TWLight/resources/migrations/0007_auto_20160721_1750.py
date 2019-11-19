# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("resources", "0006_auto_20160706_1409")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="logo_url",
            field=models.URLField(
                help_text="Optional URL of an image that can be used to represent this partner.",
                null=True,
                blank=True,
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="affiliation",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify their institutional affiliation.",
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="agreement_with_terms_of_use",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to agree with the partner's terms of use.",
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="country_of_residence",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify their countries of residence.",
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="occupation",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify their occupation.",
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="real_name",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify their real names.",
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="specific_stream",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify a particular database they want to access.",
            ),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name="partner",
            name="specific_title",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to specify a particular title they want to access.",
            ),
            preserve_default=True,
        ),
    ]
