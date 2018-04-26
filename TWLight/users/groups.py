from django.contrib.auth.models import Group

# Woo yeah named constant!
COORDINATOR_GROUP_NAME = 'Coordinators'

def get_coordinators():
    # Django will try to execute this file before syncdb has been run for the
    # first time, i.e. before the database has been set up. That means this
    # needs to be a function, not merely a statement like
    # coordinators = Group.objects.get(name=COORDINATOR_GROUP_NAME), because
    # that query will fail as Group won't exist yet.
    # The actual Coordinators group is established by a migration, so it is
    # guaranteed to exist at runtime.
    try:
        return Group.objects.get(name=COORDINATOR_GROUP_NAME)
    except:
        pass
