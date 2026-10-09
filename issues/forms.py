from django import forms
from .models import Issue, IssueStatus, Journal


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = [
            "tracker", "subject", "description", "status", "priority",
            "assigned_to", "fixed_version", "parent",
            "start_date", "due_date", "estimated_hours", "done_ratio",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._project = project
        self._applicable_custom_fields = []

        if project:
            # Limiter les versions et assignations aux membres du projet
            from versions.models import Version
            self.fields["fixed_version"].queryset = Version.objects.filter(project=project)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            member_ids = project.memberships.values_list("user_id", flat=True)
            self.fields["assigned_to"].queryset = User.objects.filter(pk__in=member_ids)
            # Limiter les parents aux tickets du même projet
            self.fields["parent"].queryset = Issue.objects.filter(project=project).exclude(
                pk=self.instance.pk if self.instance.pk else None
            )
            # Injecter les champs personnalisés
            self._inject_custom_fields(project)

        if self.instance.pk and user:
            # Restreindre les statuts selon le workflow
            allowed = self.instance.allowed_statuses_for(user)
            current_qs = IssueStatus.objects.filter(pk=self.instance.status_id)
            self.fields["status"].queryset = (allowed | current_qs).distinct()

    def _inject_custom_fields(self, project):
        from customfields.utils import (
            get_applicable_fields, build_form_field,
            get_initial_values,
        )
        tracker = self.instance.tracker if self.instance.pk else None
        applicable = list(get_applicable_fields(project, tracker))
        self._applicable_custom_fields = applicable

        if applicable and self.instance.pk:
            initial_values = get_initial_values(self.instance, applicable)
        else:
            initial_values = {}

        for cf in applicable:
            key = f"cf_{cf.pk}"
            field = build_form_field(cf)
            field.initial = initial_values.get(key, cf.default_value)
            self.fields[key] = field


class JournalNoteForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Ajouter un commentaire…"}),
        }
        labels = {"notes": ""}


class StatusUpdateForm(forms.Form):
    status_id = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, *args, allowed_statuses=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._allowed_statuses = allowed_statuses or IssueStatus.objects.none()

    def clean_status_id(self):
        pk = self.cleaned_data["status_id"]
        status = self._allowed_statuses.filter(pk=pk).first()
        if not status:
            raise forms.ValidationError("Transition non autorisée.")
        return status


class DoneRatioUpdateForm(forms.Form):
    CHOICES = [(i, f"{i}%") for i in range(0, 101, 10)]
    done_ratio = forms.ChoiceField(choices=CHOICES)

    def clean_done_ratio(self):
        return int(self.cleaned_data["done_ratio"])
