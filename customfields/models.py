from django.db import models


class CustomField(models.Model):
    FIELD_TYPES = [
        ("text",      "Texte court"),
        ("textarea",  "Texte long"),
        ("integer",   "Entier"),
        ("float",     "Nombre décimal"),
        ("date",      "Date"),
        ("bool",      "Case à cocher"),
        ("list",      "Liste déroulante"),
        ("multilist", "Liste multiple"),
    ]

    name = models.CharField("nom", max_length=255, unique=True)
    field_type = models.CharField(
        "type de champ", max_length=20, choices=FIELD_TYPES, default="text"
    )
    description = models.TextField("description / aide", blank=True)
    is_required = models.BooleanField("obligatoire", default=False)

    # Scope trackers
    is_for_all_trackers = models.BooleanField("tous les trackers", default=True)
    trackers = models.ManyToManyField(
        "issues.Tracker",
        blank=True,
        related_name="custom_fields",
        verbose_name="trackers spécifiques",
    )

    # Scope projects
    is_for_all_projects = models.BooleanField("tous les projets", default=True)
    projects = models.ManyToManyField(
        "projects.Project",
        blank=True,
        related_name="custom_fields",
        verbose_name="projets spécifiques",
    )

    # Options for list / multilist
    possible_values = models.JSONField(
        "valeurs possibles",
        default=list,
        blank=True,
        help_text="Pour les types liste : une valeur par ligne (stocké en JSON).",
    )
    default_value = models.TextField("valeur par défaut", blank=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "champ personnalisé"
        verbose_name_plural = "champs personnalisés"
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    @property
    def is_list_type(self):
        return self.field_type in ("list", "multilist")


class CustomFieldValue(models.Model):
    """Valeur d'un champ personnalisé pour un ticket donné."""
    issue = models.ForeignKey(
        "issues.Issue",
        on_delete=models.CASCADE,
        related_name="custom_values",
    )
    field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name="values",
    )
    # Toujours stocké en texte ; le décodage est fait par utils.decode_value()
    value = models.TextField(blank=True)

    class Meta:
        verbose_name = "valeur de champ personnalisé"
        unique_together = [("issue", "field")]

    def __str__(self):
        return f"{self.field.name} = {self.value!r}"
