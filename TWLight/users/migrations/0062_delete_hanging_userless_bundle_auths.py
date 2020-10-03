from django.db import migrations


def delete_hanging_bundle_auths(apps, schema_editor):
    Authorization = apps.get_model("users", "Authorization")
    Authorization.objects.filter(
        user=None,
        partners__authorization_method=3,  # using the actual number of Partner.BUNDLE
    ).distinct()  # distinct() required because partners__authorization_method is ManyToMany


class Migration(migrations.Migration):

    dependencies = [("users", "0061_make_staff_superusers_wp_eligible")]

    operations = [migrations.RunPython(delete_hanging_bundle_auths)]
