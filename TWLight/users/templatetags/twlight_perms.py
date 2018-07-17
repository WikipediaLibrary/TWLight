from django import template

from TWLight.users.groups import get_coordinators, get_restricted

register = template.Library()

@register.filter
def coordinators_only(user):
    """Return True if user is in coordinator group (or superuser), else False"""
    coordinators = get_coordinators()
    return (coordinators in user.groups.all() or
            user.is_superuser)

@register.filter
def partner_coordinator_only(user):
    """Return True if user is the coordinator for a partner"""
    coordinators = get_coordinators()
    return (coordinators in user.groups.all() or
            user.is_superuser)

@register.filter
def restricted(user):
    """Return True if user is in the restricted group, else False"""
    restricted = get_restricted()
    return restricted in user.groups.all()
