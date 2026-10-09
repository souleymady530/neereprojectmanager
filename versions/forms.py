from django import forms
from .models import Version


class VersionForm(forms.ModelForm):
    class Meta:
        model = Version
        fields = ["name", "description", "effective_date", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "effective_date": forms.DateInput(attrs={"type": "date"}),
        }
