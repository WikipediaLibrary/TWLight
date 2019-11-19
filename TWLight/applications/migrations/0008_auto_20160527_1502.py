# -*- coding: utf-8 -*-


from django.db import models, migrations


def copy_editor_data(apps, schema_editor):
    Application = apps.get_model("applications", "Application")
    for app in Application.objects.all():
        if hasattr(app.user, "editor"):
            app.editor = app.user.editor
            app.save()
        else:
            app.delete()


class Migration(migrations.Migration):

    dependencies = [("applications", "0007_application_editor")]

    operations = [migrations.RunPython(copy_editor_data)]
