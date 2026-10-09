"""
Rendu Markdown sécurisé pour le wiki.
- Supporte les extensions : toc, fenced_code, tables, nl2br, attr_list
- Transforme [[Titre de page]] en lien wiki
- Retourne (html_safe, toc_html)
"""

import re
import difflib
import markdown
import bleach
from django.utils.safestring import mark_safe
from django.utils.text import slugify

WIKILINK_RE = re.compile(r'\[\[(.+?)\]\]')

ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "ul", "ol", "li",
    "strong", "em", "del", "s", "code", "pre", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "img",
    "div", "span",
}

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id"],
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "th": ["align"],
    "td": ["align"],
    "code": ["class"],
}


def _replace_wikilinks(text, project_identifier):
    def replace(match):
        raw = match.group(1).strip()
        if "|" in raw:
            title, display = raw.split("|", 1)
            title = title.strip()
            display = display.strip()
        else:
            title = display = raw
        slug = slugify(title)
        url = f"/projects/{project_identifier}/wiki/{slug}/"
        return f"[{display}]({url})"
    return WIKILINK_RE.sub(replace, text)


def render_markdown(text, project_identifier=None):
    """
    Transforme le Markdown en HTML sécurisé.
    Retourne (html: SafeString, toc: SafeString).
    """
    if project_identifier:
        text = _replace_wikilinks(text, project_identifier)

    md = markdown.Markdown(
        extensions=["toc", "fenced_code", "tables", "nl2br", "attr_list"],
        extension_configs={
            "toc": {"title": "Table des matières", "toc_depth": 3},
        },
    )
    raw_html = md.convert(text)
    toc_html = getattr(md, "toc", "")

    clean_html = bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return mark_safe(clean_html), mark_safe(toc_html)


def diff_revisions(old_content, new_content, old_label="ancienne", new_label="nouvelle"):
    """
    Retourne un diff HTML (unified) entre deux contenus.
    Les lignes ajoutées/supprimées sont marquées avec des classes CSS.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=old_label,
        tofile=new_label,
        lineterm="",
    ))

    if not diff:
        return mark_safe('<p class="text-gray-400 text-sm">Aucune différence.</p>')

    html_lines = []
    for line in diff:
        escaped = (
            line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
        if line.startswith("+++") or line.startswith("---"):
            css = "text-gray-400"
        elif line.startswith("@@"):
            css = "text-blue-500 bg-blue-50"
        elif line.startswith("+"):
            css = "text-green-700 bg-green-50"
        elif line.startswith("-"):
            css = "text-red-700 bg-red-50"
        else:
            css = "text-gray-600"
        html_lines.append(f'<div class="{css} font-mono text-xs leading-5 px-2">{escaped}</div>')

    return mark_safe(
        '<div class="border rounded overflow-auto">' + "".join(html_lines) + "</div>"
    )
