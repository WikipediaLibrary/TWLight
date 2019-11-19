from django.core.management.commands import makemessages


class Command(makemessages.Command):
    twlight_xgettext_options = [
        str("--msgid-bugs-address=wikipedialibrary@wikimedia.org"),
        str("--package-name=TWLight"),
        str("--package-version=HEAD"),
        str("--copyright-holder=2017 Wikimedia Foundation, Inc."),
    ]
    xgettext_options = makemessages.Command.xgettext_options + twlight_xgettext_options
    makemessages.Command.xgettext_options = xgettext_options
