from django.shortcuts import render as django_render
from django.http import HttpRequest


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def render_htmx_or_redirect(request, template, context, redirect_url):
    """Retourne un partial HTMX ou redirige (fallback sans JS)."""
    from django.shortcuts import redirect
    if is_htmx(request):
        return django_render(request, template, context)
    return redirect(redirect_url)
