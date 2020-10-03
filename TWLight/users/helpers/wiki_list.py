# -*- coding: utf-8 -*-

# These were updated from wikistats.wmflabs.org/display.php?t=wp on
# 13 February 2017.

WIKIS = (
    # Machine-readable/human-readable pairs intended as options
    # for the home_wiki element on the user profile.
    ("meta", "meta.wikimedia.org"),
)

# Given the wiki code, get the base URL.
# Items look like {'en': 'en.wikipedia.org'}.
WIKI_DICT = {wiki[0]: wiki[1] for wiki in WIKIS}

LANGUAGE_CODES = {
    # For providing human-readable language names for the
    # above wikis. Note: exploits Python3 unicode support
    # to provide things like 'Bokmål'.
    "meta": "Global"
}
