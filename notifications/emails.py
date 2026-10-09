"""
Fonctions d'envoi de notifications par email.

Chaque fonction :
1. Calcule la liste des destinataires (avec vérification des préférences)
2. Rend les templates text + HTML
3. Envoie via EmailMultiAlternatives (fail_silently=True)

Convention : l'acteur (celui qui déclenche l'action) ne reçoit jamais de notification.
"""

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import NotificationPreference

logger = logging.getLogger(__name__)

SITE_URL = getattr(settings, "SITE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _get_pref(user):
    return NotificationPreference.for_user(user)


def _issue_recipients(issue, actor, pref_attr):
    """
    Retourne les adresses email à notifier pour un événement lié à un ticket.
    pref_attr : nom de l'attribut booléen sur NotificationPreference à vérifier.
    """
    candidates = set()

    if issue.author_id:
        candidates.add(issue.author)
    if issue.assigned_to_id:
        candidates.add(issue.assigned_to)
    for w in issue.watchers.select_related("user"):
        candidates.add(w.user)

    # Exclure l'acteur et les utilisateurs sans email ou ayant désactivé la notif
    recipients = []
    for user in candidates:
        if user == actor:
            continue
        if not user.email:
            continue
        pref = _get_pref(user)
        if getattr(pref, pref_attr, True):
            recipients.append(user.email)

    return list(set(recipients))


def _send(subject, template_prefix, context, recipient_list):
    """Envoie un email text+HTML à la liste de destinataires."""
    if not recipient_list:
        return

    context.setdefault("site_url", SITE_URL)

    try:
        text_body = render_to_string(f"notifications/emails/{template_prefix}.txt", context)
        html_body = render_to_string(f"notifications/emails/{template_prefix}.html", context)
    except Exception:
        logger.exception("Impossible de rendre le template email %s", template_prefix)
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("Échec d'envoi de l'email '%s' à %s", subject, recipient_list)


# ---------------------------------------------------------------------------
# Événements tickets
# ---------------------------------------------------------------------------

def notify_issue_created(issue, actor):
    """Notifie l'assigné (si différent de l'auteur) qu'un ticket lui a été attribué."""
    if not issue.assigned_to or issue.assigned_to == actor:
        return

    pref = _get_pref(issue.assigned_to)
    if not pref.notify_assigned or not issue.assigned_to.email:
        return

    _send(
        subject=f"[{issue.project.name}] Ticket #{issue.pk} assigné : {issue.subject}",
        template_prefix="issue_assigned",
        context={"issue": issue, "actor": actor, "site_url": SITE_URL},
        recipient_list=[issue.assigned_to.email],
    )


def notify_issue_updated(issue, journal, actor):
    """
    Notifie les parties prenantes d'une modification.
    journal peut être None (pas de changement enregistré).
    """
    if journal is None:
        return

    # Si le ticket a été réassigné, notifier le nouvel assigné séparément
    assigned_change = journal.details.filter(field="assigned_to").first()
    if assigned_change and assigned_change.new_value and issue.assigned_to:
        _notify_newly_assigned(issue, actor)

    recipients = _issue_recipients(issue, actor, "notify_issue_updated")
    if not recipients:
        return

    _send(
        subject=f"[{issue.project.name}] Ticket #{issue.pk} modifié : {issue.subject}",
        template_prefix="issue_updated",
        context={"issue": issue, "journal": journal, "actor": actor, "site_url": SITE_URL},
        recipient_list=recipients,
    )


def _notify_newly_assigned(issue, actor):
    if not issue.assigned_to or issue.assigned_to == actor:
        return
    pref = _get_pref(issue.assigned_to)
    if not pref.notify_assigned or not issue.assigned_to.email:
        return
    _send(
        subject=f"[{issue.project.name}] Ticket #{issue.pk} vous a été assigné : {issue.subject}",
        template_prefix="issue_assigned",
        context={"issue": issue, "actor": actor, "site_url": SITE_URL},
        recipient_list=[issue.assigned_to.email],
    )


def notify_issue_commented(issue, journal, actor):
    """Notifie les parties prenantes d'un nouveau commentaire."""
    if journal is None or not journal.notes.strip():
        return

    recipients = _issue_recipients(issue, actor, "notify_issue_commented")
    if not recipients:
        return

    _send(
        subject=f"[{issue.project.name}] Nouveau commentaire sur #{issue.pk} : {issue.subject}",
        template_prefix="issue_comment",
        context={"issue": issue, "journal": journal, "actor": actor, "site_url": SITE_URL},
        recipient_list=recipients,
    )


# ---------------------------------------------------------------------------
# Événements wiki
# ---------------------------------------------------------------------------

def notify_wiki_edited(page, revision, actor):
    """Notifie les membres du projet qui ont activé les notifications wiki."""
    from projects.models import Membership

    memberships = (
        Membership.objects.filter(project=page.project)
        .select_related("user")
        .exclude(user=actor)
    )
    recipients = []
    for m in memberships:
        user = m.user
        if not user.email:
            continue
        pref = _get_pref(user)
        if pref.notify_wiki_edited:
            recipients.append(user.email)

    if not recipients:
        return

    _send(
        subject=f"[{page.project.name}] Wiki modifié : {page.title}",
        template_prefix="wiki_edited",
        context={"page": page, "revision": revision, "actor": actor, "site_url": SITE_URL},
        recipient_list=recipients,
    )
