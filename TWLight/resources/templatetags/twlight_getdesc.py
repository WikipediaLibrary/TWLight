from django.template.defaulttags import register

@register.filter
def get_desc(desc_dict, partner_pk):
    return desc_dict.get(partner_pk)
