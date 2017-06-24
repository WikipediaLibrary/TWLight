from django import template

register = template.Library()

@register.filter
def remove_tag(value, arg):
  """Passes string through removetags filter."""
  output = template.defaultfilters.removetags(value, arg)
  return output
