from django.contrib.auth.models import Group

coordinators = Group(name='Coordinators')
# TODO when we have applications, coordinators should have view and edit permissions
