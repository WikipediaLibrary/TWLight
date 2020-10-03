from django.db import migrations


def remove_bundle_eligibility_on_users_with_unaccepted_terms(apps, schema_editor):
    Editor = apps.get_model("users", "Editor")
    for editor in Editor.objects.all():
        # If a user has not accepted the terms of use and has bundle eligibility,
        # remove the eligibility until user accepts the terms of use
        if not editor.user.userprofile.terms_of_use and editor.wp_bundle_eligible:
            editor.wp_bundle_eligible = False
            editor.save()


class Migration(migrations.Migration):

    dependencies = [("users", "0062_delete_hanging_userless_bundle_auths")]

    operations = [
        migrations.RunPython(remove_bundle_eligibility_on_users_with_unaccepted_terms)
    ]
