from django.db import models
from django.urls import reverse


class Version(models.Model):
    STATUS_OPEN = "open"
    STATUS_LOCKED = "locked"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Ouverte"),
        (STATUS_LOCKED, "Verrouillée"),
        (STATUS_CLOSED, "Fermée"),
    ]

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="versions"
    )
    name = models.CharField("nom", max_length=255)
    description = models.TextField("description", blank=True)
    effective_date = models.DateField("date de livraison", null=True, blank=True)
    status = models.CharField(
        "statut", max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "version"
        unique_together = [("project", "name")]
        ordering = ["effective_date", "name"]

    def __str__(self):
        return self.name

    @property
    def progress(self):
        """Pourcentage de tickets fermés."""
        total = self.issues.count()
        if not total:
            return 0
        closed = self.issues.filter(status__is_closed=True).count()
        return int(closed / total * 100)
