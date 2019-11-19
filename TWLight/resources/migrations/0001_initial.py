# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Contact",
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
                    "title",
                    models.CharField(
                        help_text=b"Organizational role or job title. This is NOT intended to be used for honorofics.",
                        max_length=30,
                    ),
                ),
                ("email", models.EmailField(max_length=75)),
                ("full_name", models.CharField(max_length=50)),
                (
                    "short_name",
                    models.CharField(
                        help_text=b"The form of the contact person's name to use in email greetings (as in 'Hi Jake')",
                        max_length=15,
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Partner",
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
                    "company_name",
                    models.CharField(
                        help_text=b"Partner organization's name (e.g. McFarland). Note: this will be user-visible and *not translated*.",
                        max_length=30,
                    ),
                ),
                (
                    "terms_of_use",
                    models.URLField(
                        help_text=b"Required if this company requires that users agree to terms of use as a condition of applying for access; optional otherwise.",
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        help_text=b"Optional description of this partner's offerings.",
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "mutually_exclusive",
                    models.NullBooleanField(
                        default=None,
                        help_text=b"If True, users can only apply for one Stream at a time from this Partner. If False, users can apply for multiple Streams at a time. This field must be filled in when Partners have multiple Streams, but may be left blank otherwise.",
                    ),
                ),
                ("real_name", models.BooleanField(default=False)),
                ("country_of_residence", models.BooleanField(default=False)),
                ("specific_title", models.BooleanField(default=False)),
                ("specific_stream", models.BooleanField(default=False)),
                ("occupation", models.BooleanField(default=False)),
                ("affiliation", models.BooleanField(default=False)),
                ("agreement_with_terms_of_use", models.BooleanField(default=False)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Stream",
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
                    "name",
                    models.CharField(
                        help_text=b"Name of stream (e.g. 'Health and Behavioral Sciences.Will be user-visible and *not translated*. Do not include the name of the partner here. If partner name and resource name need to be presented together, templates are responsible for presenting them in a format that can be internationalized.",
                        max_length=50,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        help_text=b"Optional description of this stream's contents.",
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "partner",
                    models.ForeignKey(related_name="streams", to="resources.Partner"),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name="contact",
            name="partner",
            field=models.ForeignKey(related_name="contacts", to="resources.Partner"),
            preserve_default=True,
        ),
    ]
