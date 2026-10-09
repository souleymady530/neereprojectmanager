from django import forms
from django.contrib.auth import get_user_model

from .models import Report, AVAILABLE_COLUMNS, DEFAULT_COLUMNS
from issues.models import Tracker, IssueStatus, IssuePriority
from projects.models import Project
from versions.models import Version

User = get_user_model()

IS_EVALUATED_CHOICES = [
    ("", "Tous"),
    ("true", "Oui"),
    ("false", "Non"),
]


class ReportForm(forms.ModelForm):
    # ── Colonnes ──────────────────────────────────────────────
    columns = forms.MultipleChoiceField(
        choices=AVAILABLE_COLUMNS,
        widget=forms.CheckboxSelectMultiple,
        initial=DEFAULT_COLUMNS,
        label="Colonnes à afficher",
    )

    # ── Filtres ───────────────────────────────────────────────
    f_subject = forms.CharField(label="Sujet contient", required=False)
    f_tracker = forms.ModelMultipleChoiceField(
        queryset=Tracker.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tracker",
    )
    f_status = forms.ModelMultipleChoiceField(
        queryset=IssueStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Statut",
    )
    f_priority = forms.ModelMultipleChoiceField(
        queryset=IssuePriority.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Priorité",
    )
    f_assigned_to = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Assigné à",
        empty_label="— Tous —",
    )
    f_fixed_version = forms.ModelChoiceField(
        queryset=Version.objects.all(),
        required=False,
        label="Version cible",
        empty_label="— Toutes —",
    )
    f_open_only = forms.BooleanField(required=False, label="Tickets ouverts seulement")
    f_is_evaluated = forms.ChoiceField(
        choices=IS_EVALUATED_CHOICES,
        required=False,
        label="Évalué",
    )
    f_start_date_after = forms.DateField(
        required=False,
        label="Date début après le",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    f_start_date_before = forms.DateField(
        required=False,
        label="Date début avant le",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    f_due_date_after = forms.DateField(
        required=False,
        label="Échéance après le",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    f_due_date_before = forms.DateField(
        required=False,
        label="Échéance avant le",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Report
        fields = ["name", "project"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from projects.models import Membership
            project_ids = Membership.objects.filter(user=user).values_list("project_id", flat=True)
            self.fields["project"].queryset = Project.objects.filter(pk__in=project_ids)
        self.fields["project"].required = False
        self.fields["project"].empty_label = "— Global (tous projets visibles) —"

        # Pré-remplir depuis l'instance existante
        instance = kwargs.get("instance")
        if instance and instance.pk:
            self.fields["columns"].initial = instance.columns
            f = instance.filters
            if f.get("subject"):
                self.fields["f_subject"].initial = f["subject"]
            if f.get("tracker"):
                self.fields["f_tracker"].initial = f["tracker"]
            if f.get("status"):
                self.fields["f_status"].initial = f["status"]
            if f.get("priority"):
                self.fields["f_priority"].initial = f["priority"]
            if f.get("assigned_to"):
                self.fields["f_assigned_to"].initial = f["assigned_to"]
            if f.get("fixed_version"):
                self.fields["f_fixed_version"].initial = f["fixed_version"]
            if f.get("open_only"):
                self.fields["f_open_only"].initial = True
            if "is_evaluated" in f:
                self.fields["f_is_evaluated"].initial = "true" if f["is_evaluated"] else "false"
            if f.get("start_date_after"):
                self.fields["f_start_date_after"].initial = f["start_date_after"]
            if f.get("start_date_before"):
                self.fields["f_start_date_before"].initial = f["start_date_before"]
            if f.get("due_date_after"):
                self.fields["f_due_date_after"].initial = f["due_date_after"]
            if f.get("due_date_before"):
                self.fields["f_due_date_before"].initial = f["due_date_before"]

    def save(self, commit=True):
        report = super().save(commit=False)
        d = self.cleaned_data
        filters = {}
        if d.get("f_subject"):
            filters["subject"] = d["f_subject"]
        if d.get("f_tracker"):
            filters["tracker"] = [t.pk for t in d["f_tracker"]]
        if d.get("f_status"):
            filters["status"] = [s.pk for s in d["f_status"]]
        if d.get("f_priority"):
            filters["priority"] = [p.pk for p in d["f_priority"]]
        if d.get("f_assigned_to"):
            filters["assigned_to"] = d["f_assigned_to"].pk
        if d.get("f_fixed_version"):
            filters["fixed_version"] = d["f_fixed_version"].pk
        if d.get("f_open_only"):
            filters["open_only"] = True
        if d.get("f_is_evaluated"):
            filters["is_evaluated"] = d["f_is_evaluated"] == "true"
        if d.get("f_start_date_after"):
            filters["start_date_after"] = str(d["f_start_date_after"])
        if d.get("f_start_date_before"):
            filters["start_date_before"] = str(d["f_start_date_before"])
        if d.get("f_due_date_after"):
            filters["due_date_after"] = str(d["f_due_date_after"])
        if d.get("f_due_date_before"):
            filters["due_date_before"] = str(d["f_due_date_before"])
        report.filters = filters
        report.columns = d["columns"]
        if commit:
            report.save()
        return report
