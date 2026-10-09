from django import forms
from .models import Project, Membership, Role, PERMISSION_CODES, ALL_PERMISSIONS


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "identifier", "description", "parent", "is_public"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclure le projet lui-même des sous-projets possibles
        if self.instance.pk:
            self.fields["parent"].queryset = Project.objects.exclude(pk=self.instance.pk)


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ["user", "roles"]
        widgets = {
            "roles": forms.CheckboxSelectMultiple(),
        }


class RoleForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(
        choices=ALL_PERMISSIONS,
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Permissions",
    )

    class Meta:
        model = Role
        fields = ["name", "permissions", "position"]
