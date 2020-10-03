from django import template

import re

register = template.Library()


@register.filter()
def twlight_removetags(value, tags):
    """Returns the given HTML with given tags removed."""
    tags = [re.escape(tag) for tag in tags.split()]
    tags_re = "(%s)" % "|".join(tags)
    starttag_re = re.compile(r"<%s(/?>|(\s+[^>]*>))" % tags_re, re.U)
    endtag_re = re.compile("</%s>" % tags_re)
    output = starttag_re.sub("", value)
    output = endtag_re.sub("", output)
    return output
