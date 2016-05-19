from django import template

from TWLight.users.groups import get_coordinators

register = template.Library()

@register.filter
def coordinators_only(user):
    """Return True if user is in coordinator group (or superuser), else False"""
    coordinators = get_coordinators()
    return (coordinators in user.groups.all() or
            user.is_superuser)
