from django.db import migrations


def turn_staff_superusers_bundle_eligible(apps, schema_editor):
    Editor = apps.get_model("users", "Editor")
    for editor in Editor.objects.all():
        if editor.user.is_staff or editor.user.is_superuser:
            editor.wp_bundle_eligible = True
            editor.save()


class Migration(migrations.Migration):

    dependencies = [("users", "0060_auto_20200804_1634")]

    operations = [migrations.RunPython(turn_staff_superusers_bundle_eligible)]
