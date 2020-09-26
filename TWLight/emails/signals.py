from django.dispatch import Signal


class ContactUs(object):
    new_email = Signal(
        providing_args=["user_email", "cc", "editor_wp_username", "body"]
    )
