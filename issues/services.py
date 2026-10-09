"""
Service de mise à jour des tickets.
Centralise la journalisation des modifications.

Usage :
    from issues.services import update_issue
    update_issue(issue, request.user, {"status": new_status, "priority": new_priority}, note="...")
"""

from .models import Issue, Journal, JournalDetail


TRACKED_FIELDS = {
    "status": ("status_id", lambda v: str(v) if v else None),
    "priority": ("priority_id", lambda v: str(v) if v else None),
    "tracker": ("tracker_id", lambda v: str(v) if v else None),
    "assigned_to": ("assigned_to_id", lambda v: str(v) if v else None),
    "fixed_version": ("fixed_version_id", lambda v: str(v) if v else None),
    "subject": ("subject", str),
    "description": ("description", str),
    "start_date": ("start_date", lambda v: str(v) if v else None),
    "due_date": ("due_date", lambda v: str(v) if v else None),
    "estimated_hours": ("estimated_hours", lambda v: str(v) if v else None),
    "done_ratio": ("done_ratio", str),
    "parent": ("parent_id", lambda v: str(v) if v else None),
}


def update_issue(issue: Issue, user, data: dict, note: str = "") -> Journal | None:
    """
    Met à jour un ticket, journalise les modifications et retourne le Journal créé.
    `data` est un dict {nom_de_champ: nouvelle_valeur} avec des instances de modèles
    (ex. {"status": <IssueStatus>}) ou des valeurs scalaires (ex. {"done_ratio": 50}).
    Retourne None si aucune modification et aucune note.
    """
    details = []

    for field_name, new_value in data.items():
        if field_name not in TRACKED_FIELDS:
            continue
        attr, formatter = TRACKED_FIELDS[field_name]
        old_value = getattr(issue, attr)
        # Pour les FK, comparer les IDs
        if hasattr(new_value, "pk"):
            new_id = new_value.pk
        else:
            new_id = new_value

        if old_value != new_id:
            details.append(
                JournalDetail(
                    field=field_name,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_id) if new_id is not None else None,
                )
            )
            setattr(issue, field_name if not attr.endswith("_id") else field_name, new_value)

    if not details and not note:
        return None

    issue.save()

    journal = Journal.objects.create(issue=issue, user=user, notes=note)
    for detail in details:
        detail.journal = journal
    JournalDetail.objects.bulk_create(details)

    return journal
