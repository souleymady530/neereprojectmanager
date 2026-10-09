"""
Fonctions utilitaires pour les champs personnalisés.

- get_applicable_fields(project, tracker=None)  → QuerySet<CustomField>
- build_form_field(cf)                          → Django form field
- encode_value(cf, python_value)                → str  (pour le stockage)
- decode_value(cf, raw_str)                     → Python value (pour le formulaire)
- save_custom_values(issue, cleaned_data, fields) → list[(cf, old, new)]
- get_display_values(issue)                     → list[(CustomField, display_str)]
"""

import json


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------

def get_applicable_fields(project, tracker=None):
    """
    Retourne les CustomFields actifs pour la combinaison projet + tracker.
    Si tracker=None, retourne tous les champs qui s'appliquent au projet
    (quel que soit le tracker).
    """
    from .models import CustomField

    # Filtre projet
    qs = CustomField.objects.filter(is_for_all_projects=True)
    if project:
        qs = (qs | CustomField.objects.filter(projects=project)).distinct()

    # Filtre tracker
    if tracker is not None:
        tracker_qs = qs.filter(is_for_all_trackers=True)
        tracker_qs = (tracker_qs | qs.filter(trackers=tracker)).distinct()
        qs = tracker_qs

    return qs.order_by("position", "name")


# ---------------------------------------------------------------------------
# Form field builder
# ---------------------------------------------------------------------------

def build_form_field(cf):
    """
    Construit le champ de formulaire Django correspondant à un CustomField.
    """
    from django import forms

    base = {
        "label": cf.name,
        "required": cf.is_required,
        "help_text": cf.description,
    }

    ft = cf.field_type

    if ft == "text":
        return forms.CharField(max_length=255, **base)

    if ft == "textarea":
        return forms.CharField(
            widget=forms.Textarea(attrs={"rows": 3}), **base
        )

    if ft == "integer":
        return forms.IntegerField(**base)

    if ft == "float":
        return forms.DecimalField(**base)

    if ft == "date":
        return forms.DateField(
            widget=forms.DateInput(attrs={"type": "date"}), **base
        )

    if ft == "bool":
        base["required"] = False  # une case à cocher n'est jamais obligatoire au sens HTML
        return forms.BooleanField(**base)

    if ft == "list":
        choices = [("", "—")] + [(v, v) for v in (cf.possible_values or [])]
        return forms.ChoiceField(choices=choices, **base)

    if ft == "multilist":
        choices = [(v, v) for v in (cf.possible_values or [])]
        return forms.MultipleChoiceField(
            choices=choices,
            widget=forms.CheckboxSelectMultiple,
            **base,
        )

    # Fallback texte court
    return forms.CharField(max_length=255, **base)


# ---------------------------------------------------------------------------
# Encode / decode
# ---------------------------------------------------------------------------

def encode_value(cf, python_value):
    """
    Convertit une valeur Python (issue de cleaned_data) en chaîne pour le stockage.
    """
    if python_value is None or python_value == "":
        return ""
    if cf.field_type == "multilist":
        return json.dumps(list(python_value))
    if cf.field_type == "bool":
        return "1" if python_value else "0"
    return str(python_value)


def decode_value(cf, raw):
    """
    Convertit la chaîne stockée en valeur Python pour l'initial du formulaire.
    """
    if raw is None or raw == "":
        if cf.field_type == "bool":
            return False
        if cf.field_type == "multilist":
            return []
        return ""
    if cf.field_type == "multilist":
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if cf.field_type == "bool":
        return raw == "1"
    return raw


def human_value(cf, raw):
    """
    Retourne la valeur lisible pour l'affichage (template).
    """
    if raw is None or raw == "":
        return "–"
    if cf.field_type == "multilist":
        try:
            items = json.loads(raw)
            return ", ".join(items) if items else "–"
        except (json.JSONDecodeError, TypeError):
            return raw
    if cf.field_type == "bool":
        return "Oui" if raw == "1" else "Non"
    return raw


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_custom_values(issue, cleaned_data, applicable_fields):
    """
    Persiste les CustomFieldValue depuis les données nettoyées du formulaire.

    Retourne une liste de tuples (CustomField, old_raw, new_raw) pour
    les champs qui ont changé — utile pour la journalisation.
    """
    from .models import CustomFieldValue

    existing = {
        cv.field_id: cv
        for cv in CustomFieldValue.objects.filter(
            issue=issue, field__in=applicable_fields
        )
    }
    changes = []

    for cf in applicable_fields:
        key = f"cf_{cf.pk}"
        if key not in cleaned_data:
            continue

        new_raw = encode_value(cf, cleaned_data[key])
        cv = existing.get(cf.pk)
        old_raw = cv.value if cv else ""

        if new_raw == old_raw:
            continue

        changes.append((cf, old_raw, new_raw))

        if cv:
            cv.value = new_raw
            cv.save(update_fields=["value"])
        else:
            CustomFieldValue.objects.create(issue=issue, field=cf, value=new_raw)

    return changes


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def get_display_values(issue):
    """
    Retourne [(CustomField, display_str)] pour les champs qui ont une valeur
    non vide, triés par position.
    """
    values = {
        cv.field_id: cv.value
        for cv in issue.custom_values.select_related("field")
    }
    result = []
    fields = get_applicable_fields(issue.project, issue.tracker)
    for cf in fields:
        raw = values.get(cf.pk, "")
        display = human_value(cf, raw)
        if display != "–":
            result.append((cf, display))
    return result


def get_initial_values(issue, applicable_fields):
    """
    Retourne {f"cf_{cf.pk}": python_value} pour pré-remplir le formulaire.
    """
    raw_map = {
        cv.field_id: cv.value
        for cv in issue.custom_values.filter(field__in=applicable_fields)
    }
    return {
        f"cf_{cf.pk}": decode_value(cf, raw_map.get(cf.pk, cf.default_value))
        for cf in applicable_fields
    }
