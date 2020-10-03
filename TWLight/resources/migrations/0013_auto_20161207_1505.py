# -*- coding: utf-8 -*-
"""
Migration #12 created the status field on Partner. It defaults to NOT_AVAILABLE,
so as to avoid accidentally exposing Partners that aren't yet open for
applications. However, all Partners existing in the database already need to be
set as AVAILABLE.
"""


from django.db import models, migrations


def fix_partner_status(apps, schema_editor):
    Partner = apps.get_model("resources", "Partner")
    for partner in Partner.objects.all():
        # This should be Partner.AVAILABLE. We can't reference that directly
        # since it's not available to the migrations, though. Careful!
        partner.status = 0
        partner.save()


class Migration(migrations.Migration):

    dependencies = [("resources", "0012_partner_status")]

    operations = [migrations.RunPython(fix_partner_status)]
