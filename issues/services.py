"""
Service de mise à jour des tickets.
Centralise la journalisation des modifications.

Usage :
    from issues.services import update_issue
    update_issue(issue, request.user, {"status": new_status, "priority": new_priority}, note="...")
"""

from .models import Issue, Journal, JournalDetail


# ── Champs tracés ────────────────────────────────────────────────────────────
# Structure : field_name → (id_attr, label_fr, get_old_label_fn, get_new_label_fn)
#
# get_old_label_fn(issue)  → valeur lisible de l'ancien état
# get_new_label_fn(value)  → valeur lisible du nouvel état (value = objet ou scalaire)

TRACKED_FIELDS = {
    "status": (
        "status_id",
        "Statut",
        lambda issue: str(issue.status) if issue.status_id else None,
        lambda v: str(v) if v else None,
    ),
    "priority": (
        "priority_id",
        "Priorité",
        lambda issue: str(issue.priority) if issue.priority_id else None,
        lambda v: str(v) if v else None,
    ),
    "tracker": (
        "tracker_id",
        "Tracker",
        lambda issue: str(issue.tracker) if issue.tracker_id else None,
        lambda v: str(v) if v else None,
    ),
    "assigned_to": (
        "assigned_to_id",
        "Assigné à",
        lambda issue: issue.assigned_to.get_full_name() if issue.assigned_to_id else None,
        lambda v: v.get_full_name() if v else None,
    ),
    "fixed_version": (
        "fixed_version_id",
        "Version cible",
        lambda issue: str(issue.fixed_version) if issue.fixed_version_id else None,
        lambda v: str(v) if v else None,
    ),
    "subject": (
        "subject",
        "Sujet",
        lambda issue: issue.subject,
        lambda v: str(v) if v is not None else None,
    ),
    "description": (
        "description",
        "Description",
        lambda issue: (issue.description[:80] + "…") if issue.description and len(issue.description) > 80 else issue.description,
        lambda v: (str(v)[:80] + "…") if v and len(str(v)) > 80 else (str(v) if v is not None else None),
    ),
    "start_date": (
        "start_date",
        "Date de début",
        lambda issue: issue.start_date.strftime("%d/%m/%Y") if issue.start_date else None,
        lambda v: v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else (str(v) if v else None),
    ),
    "due_date": (
        "due_date",
        "Date d'échéance",
        lambda issue: issue.due_date.strftime("%d/%m/%Y") if issue.due_date else None,
        lambda v: v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else (str(v) if v else None),
    ),
    "estimated_hours": (
        "estimated_hours",
        "Heures estimées",
        lambda issue: f"{issue.estimated_hours}h" if issue.estimated_hours is not None else None,
        lambda v: f"{v}h" if v is not None else None,
    ),
    "done_ratio": (
        "done_ratio",
        "Avancement",
        lambda issue: f"{issue.done_ratio}%",
        lambda v: f"{v}%" if v is not None else None,
    ),
    "parent": (
        "parent_id",
        "Ticket parent",
        lambda issue: f"#{issue.parent_id}" if issue.parent_id else None,
        lambda v: f"#{v.pk}" if v else None,
    ),
    "is_evaluated": (
        "is_evaluated",
        "Évalué",
        lambda issue: str(issue.is_evaluated),
        lambda v: str(v),
    ),
}


def update_issue(issue: Issue, user, data: dict, note: str = "") -> Journal | None:
    """
    Met à jour un ticket, journalise les modifications et retourne le Journal créé.
    `data` est un dict {nom_de_champ: nouvelle_valeur} avec des instances de modèles
    (ex. {"status": <IssueStatus>}) ou des valeurs scalaires (ex. {"done_ratio": 50}).
    Retourne None si aucune modification et aucune note.
    """
    # Recharger depuis la DB : Django's ModelForm.is_valid() modifie l'instance
    # en place, donc issue porte déjà les nouvelles valeurs à ce stade.
    try:
        old = Issue.objects.get(pk=issue.pk)
    except Issue.DoesNotExist:
        old = issue

    details = []

    for field_name, new_value in data.items():
        if field_name not in TRACKED_FIELDS:
            continue

        id_attr, label_fr, get_old_label, get_new_label = TRACKED_FIELDS[field_name]

        # Comparer l'ancienne valeur (DB) avec la nouvelle valeur du formulaire
        old_id = getattr(old, id_attr)
        new_id = new_value.pk if hasattr(new_value, "pk") else new_value

        if old_id == new_id:
            continue

        # Stocker des libellés lisibles
        old_label = get_old_label(old)
        new_label = get_new_label(new_value)

        details.append(JournalDetail(
            field=field_name,
            old_value=old_label,
            new_value=new_label,
        ))

    # Sauvegarder quoi qu'il arrive (l'instance a déjà les nouvelles valeurs)
    issue.save()

    if not details and not note:
        return None

    journal = Journal.objects.create(issue=issue, user=user, notes=note)
    for detail in details:
        detail.journal = journal
    JournalDetail.objects.bulk_create(details)

    return journal
