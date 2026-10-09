from django import forms
from .models import CustomField


class CustomFieldAdminForm(forms.ModelForm):
    """
    Formulaire d'administration pour créer / modifier un CustomField.
    Le champ possible_values est exposé comme un Textarea (une valeur par ligne)
    et converti en liste JSON à la validation.
    """
    possible_values_text = forms.CharField(
        label="Valeurs possibles",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Une valeur par ligne…"}),
        required=False,
        help_text="Uniquement pour les types « Liste » et « Liste multiple ».",
    )

    class Meta:
        model = CustomField
        fields = [
            "name", "field_type", "description",
            "is_required",
            "is_for_all_trackers", "trackers",
            "is_for_all_projects", "projects",
            "default_value", "position",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "trackers": forms.CheckboxSelectMultiple,
            "projects": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-remplir le textarea avec les valeurs existantes
        if self.instance.pk and self.instance.possible_values:
            self.fields["possible_values_text"].initial = "\n".join(
                self.instance.possible_values
            )

    def clean_possible_values_text(self):
        text = self.cleaned_data.get("possible_values_text", "")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines  # returns a list

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.possible_values = self.cleaned_data["possible_values_text"]
        if commit:
            instance.save()
            self._save_m2m()
        return instance
