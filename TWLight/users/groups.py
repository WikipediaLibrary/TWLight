from django.contrib.auth.models import Group

# Woo yeah named constant!
COORDINATOR_GROUP_NAME = "Coordinators"
# Woo yeah another named constant!
RESTRICTED_GROUP_NAME = "Restricted"

# Django will try to execute this file before syncdb has been run for the
# first time, i.e. before the database has been set up. That means this
# needs to be functions, not merely statements like
# coordinators = Group.objects.get(name=COORDINATOR_GROUP_NAME), because
# that query will fail as Group won't exist yet.
# The actual groups are established by a migration, so they are
# guaranteed to exist at runtime.


def get_coordinators():
    try:
        return Group.objects.get(name=COORDINATOR_GROUP_NAME)
    except:
        pass


def get_restricted():
    try:
        return Group.objects.get(name=RESTRICTED_GROUP_NAME)
    except:
        pass
