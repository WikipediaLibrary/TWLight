from django.core.management.commands import makemessages

class Command(makemessages.Command):
    twlight_xgettext_options = [
        unicode('--msgid-bugs-address=wikipedialibrary@wikimedia.org'),
        unicode('--package-name=TWLight'),
        unicode('--package-version=HEAD'),
        unicode('--copyright-holder=2017 Wikimedia Foundation, Inc.'),
    ]
    xgettext_options =  makemessages.Command.xgettext_options + twlight_xgettext_options
    makemessages.Command.xgettext_options = xgettext_options
