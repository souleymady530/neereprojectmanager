from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """{{ my_dict|get_item:key }} — accès dict par clé variable dans les templates."""
    return dictionary.get(key, [])


@register.filter
def render_md(value):
    """Rend du Markdown en HTML sécurisé (sans wikilinks)."""
    if not value:
        return ""
    from wiki.utils import render_markdown
    html, _ = render_markdown(value)
    return html
