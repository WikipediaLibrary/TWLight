import django.dispatch

class Reminder(object):
    coordinator_reminder = django.dispatch.Signal(providing_args=['app_status', 'app_count', 'coordinator_wp_username', 'coordinator_email', 'coordinator_lang'])
