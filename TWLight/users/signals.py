import django.dispatch

class Notice(object):
    user_renewal_notice = django.dispatch.Signal(providing_args=['user_wp_username', 'user_email', 'user_lang', 'partner_name', 'partner_link'])
