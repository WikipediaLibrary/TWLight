from django import template

from TWLight.users.groups import get_coordinators, get_restricted

register = template.Library()


@register.filter
def coordinators_only(user):
    """Return True if user is in coordinator group (or superuser), else False"""
    is_coordinator = False
    if user:
        coordinators = get_coordinators()
        is_coordinator = coordinators in user.groups.all() or user.is_superuser
    return is_coordinator


@register.filter
def restricted(user):
    """Return True if user is in the restricted group, else False"""
    is_restricted = False
    if user:
        restricted = get_restricted()
        is_restricted = restricted in user.groups.all()
    return is_restricted
