import datetime
from django import forms
from .models import TimeEntry, TimeActivity


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ["issue", "activity", "hours", "spent_on", "comment"]
        widgets = {
            "spent_on": forms.DateInput(attrs={"type": "date"}),
            "comment": forms.Textarea(attrs={"rows": 3}),
            "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0.25"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Valeur par défaut : aujourd'hui
        if not self.instance.pk:
            self.fields["spent_on"].initial = datetime.date.today()

        # Activité par défaut
        default_activity = TimeActivity.objects.filter(is_default=True).first()
        if default_activity and not self.instance.pk:
            self.fields["activity"].initial = default_activity

        if project:
            # Limiter les tickets à ceux du projet
            from issues.models import Issue
            self.fields["issue"].queryset = (
                Issue.objects.filter(project=project)
                .select_related("tracker")
                .order_by("-updated_at")
            )
            self.fields["issue"].label_from_instance = lambda obj: f"#{obj.pk} {obj.subject}"
        else:
            self.fields["issue"].queryset = (
                self.fields["issue"].queryset.none()
            )

    def clean_hours(self):
        hours = self.cleaned_data["hours"]
        if hours <= 0:
            raise forms.ValidationError("Les heures doivent être supérieures à 0.")
        return hours
