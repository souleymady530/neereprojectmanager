from django import forms
from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            "notify_assigned",
            "notify_issue_updated",
            "notify_issue_commented",
            "notify_wiki_edited",
        ]
        widgets = {
            f: forms.CheckboxInput(attrs={"class": "rounded border-gray-300 text-blue-600"})
            for f in fields
        }
