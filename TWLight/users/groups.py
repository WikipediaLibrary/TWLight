from django.contrib.auth.models import Group
from django.db.utils import ProgrammingError
# Woo yeah named constant!
COORDINATOR_GROUP_NAME = 'Coordinators'

try:
    coordinators = Group.objects.get(name=COORDINATOR_GROUP_NAME)
except ProgrammingError:
    # Django will try to execute this file before syncdb has been run for the
    # first time, i.e. before the database has been set up. That will
    # cause the above query to fail, because Group won't exist yet. Bleah.
    # In production, we can count on the coordinators group existing because we
    # set it up in users/migrations.
    pass
