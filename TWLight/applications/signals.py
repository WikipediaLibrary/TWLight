import django.dispatch

class Reminder(object):
    coordinator_reminder = django.dispatch.Signal(providing_args=['app'])
