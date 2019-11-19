from django import template

from TWLight.applications.models import Application

register = template.Library()


@register.filter
def get_status_display_for_version(version):
    try:
        status = version.field_dict["status"]
        return Application.STATUS_CHOICES[status][1]
    except:
        return None


@register.filter
def get_bootstrap_class_for_version(version):
    try:
        status = version.field_dict["status"]
        return Application.LABELMAKER[status]
    except:
        return None
