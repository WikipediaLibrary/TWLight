from django.dispatch import Signal

class ContactUs(object):
    new_email = Signal(providing_args=['user_email', 'editor_wp_username', 'body'])