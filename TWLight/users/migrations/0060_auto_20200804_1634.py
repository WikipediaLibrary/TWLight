# Generated by Django 3.0.9 on 2020-08-04 16:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0063_auto_20190220_1639_squashed_0084_auto_20201019_1310"),
        ("users", "0059_auto_20200706_1659"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authorization",
            name="partners",
            field=models.ManyToManyField(
                blank=True,
                help_text="The partner(s) for which the editor is authorized.",
                limit_choices_to=models.Q(status__in=[0, 2]),
                to="resources.Partner",
            ),
        ),
        migrations.AlterField(
            model_name="authorization",
            name="stream",
            field=models.ForeignKey(
                blank=True,
                help_text="The stream for which the editor is authorized.",
                limit_choices_to=models.Q(partner__status__in=[0, 2]),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="resources.Stream",
            ),
        ),
    ]
