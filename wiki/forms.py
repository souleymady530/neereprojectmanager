from django import forms


class WikiPageEditForm(forms.Form):
    title = forms.CharField(
        label="Titre",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "w-full border border-gray-300 rounded px-3 py-2 text-sm"}),
    )
    content = forms.CharField(
        label="",
        widget=forms.Textarea(attrs={
            "rows": 24,
            "class": "w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono",
            "id": "wiki-content",
            "placeholder": "Contenu en Markdown…\n\n# Titre\n\nLien vers une autre page : [[Titre de la page]]",
        }),
    )
    comment = forms.CharField(
        label="Commentaire d'édition",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            "placeholder": "Résumé des modifications (optionnel)",
            "class": "w-full border border-gray-300 rounded px-3 py-2 text-sm",
        }),
    )
