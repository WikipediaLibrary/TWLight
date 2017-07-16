from django import template

import pypandoc

register = template.Library()

@register.filter
def twlight_wikicode2html(value):
  """Passes string through pandoc and returns html"""
  output = pypandoc.convert(value, 'html', format='mediawiki')
  return output
