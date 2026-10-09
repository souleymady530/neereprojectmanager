from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """{{ my_dict|get_item:key }} — accès dict par clé variable dans les templates."""
    return dictionary.get(key, [])
