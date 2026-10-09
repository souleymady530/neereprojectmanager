from django.conf import settings
from django.db import models
from django.urls import reverse


AVAILABLE_COLUMNS = [
    ("subject", "Sujet"),
    ("tracker", "Tracker"),
    ("status", "Statut"),
    ("priority", "Priorité"),
    ("assigned_to", "Assigné à"),
    ("fixed_version", "Version cible"),
    ("project", "Projet"),
    ("start_date", "Date début"),
    ("due_date", "Date échéance"),
    ("estimated_hours", "Heures estimées"),
    ("done_ratio", "Avancement"),
    ("is_evaluated", "Évalué"),
    ("author", "Auteur"),
    ("created_at", "Créé le"),
    ("updated_at", "Mis à jour"),
]

COLUMN_LABELS = dict(AVAILABLE_COLUMNS)

DEFAULT_COLUMNS = ["subject", "tracker", "status", "priority", "assigned_to"]


class Report(models.Model):
    name = models.CharField("nom", max_length=200)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="propriétaire",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name="projet",
    )
    filters = models.JSONField("filtres", default=dict)
    columns = models.JSONField("colonnes", default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "rapport"
        verbose_name_plural = "rapports"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("reports:detail", kwargs={"pk": self.pk})
