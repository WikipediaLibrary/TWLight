from django.template.defaulttags import register

@register.filter
def get_short_desc(short_desc_dict, partner_pk):
    return short_desc_dict.get(partner_pk)