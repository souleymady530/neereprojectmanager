"""
Service wiki : création et modification de pages avec versionnage.

Usage :
    from wiki.services import edit_wiki_page, rollback_wiki_page
    page, revision = edit_wiki_page(project, user, title="Accueil", content="# Accueil\n...")
    page, revision = edit_wiki_page(project, user, title=page.title, content="...", existing_page=page)
"""

from django.db import models as db_models
from django.db import transaction
from django.utils.text import slugify


@transaction.atomic
def edit_wiki_page(project, user, title, content, comment="", existing_page=None):
    """
    Crée ou met à jour une page wiki.
    Retourne (page, revision).
    """
    from .models import WikiPage, WikiPageRevision

    if existing_page is None:
        page = WikiPage.objects.create(
            project=project,
            title=title,
            slug=slugify(title),
            created_by=user,
        )
    else:
        page = existing_page
        if page.title != title:
            page.title = title
            page.save(update_fields=["title", "updated_at"])

    last_version = (
        WikiPageRevision.objects.filter(page=page)
        .aggregate(v=db_models.Max("version"))["v"]
        or 0
    )

    revision = WikiPageRevision.objects.create(
        page=page,
        version=last_version + 1,
        content=content,
        author=user,
        comment=comment,
    )

    from notifications.emails import notify_wiki_edited
    notify_wiki_edited(page, revision, actor=user)

    return page, revision


@transaction.atomic
def rollback_wiki_page(page, target_revision, user):
    """Crée une nouvelle révision avec le contenu d'une révision antérieure."""
    return edit_wiki_page(
        project=page.project,
        user=user,
        title=page.title,
        content=target_revision.content,
        comment=f"Retour à la version {target_revision.version}",
        existing_page=page,
    )
