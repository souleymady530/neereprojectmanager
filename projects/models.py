import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


ALL_PERMISSIONS = [
    ("view_issues", "Voir les tickets"),
    ("add_issues", "Créer des tickets"),
    ("edit_issues", "Modifier les tickets"),
    ("delete_issues", "Supprimer les tickets"),
    ("log_time", "Saisir du temps"),
    ("view_time_entries", "Voir les temps"),
    ("manage_members", "Gérer les membres"),
    ("manage_versions", "Gérer les versions"),
    ("manage_project", "Gérer le projet"),
    ("view_wiki", "Voir le wiki"),
    ("edit_wiki", "Éditer le wiki"),
    ("delete_wiki_pages", "Supprimer des pages wiki"),
]

PERMISSION_CODES = [code for code, _ in ALL_PERMISSIONS]


class Role(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    permissions = models.JSONField(
        "permissions",
        default=list,
        help_text="Liste de codes : view_issues, add_issues, edit_issues…",
    )
    position = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "rôle"
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Actif"),
        (STATUS_ARCHIVED, "Archivé"),
    ]

    name = models.CharField("nom", max_length=255)
    identifier = models.SlugField(
        "identifiant",
        max_length=100,
        unique=True,
        help_text="Identifiant unique utilisé dans les URL (ex : mon-projet)",
    )
    description = models.TextField("description", blank=True)
    issue_prefix = models.CharField(
        "préfixe tickets",
        max_length=20,
        blank=True,
        help_text="Préfixe pour les noms de branche git (ex: RIIBO → branche RIIBO-12)",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="sous-projet de",
    )
    is_public = models.BooleanField("public", default=True)
    status = models.CharField(
        "statut", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
        verbose_name="créé par",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "projet"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.identifier:
            self.identifier = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("projects:overview", kwargs={"identifier": self.identifier})

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="utilisateur",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="projet",
    )
    roles = models.ManyToManyField(Role, verbose_name="rôles", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "membre"
        verbose_name_plural = "membres"
        unique_together = [("user", "project")]

    def __str__(self):
        return f"{self.user} → {self.project}"


class ProjectInvitation(models.Model):
    """Lien d'invitation unique permettant à quelqu'un de s'inscrire et rejoindre un projet."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="invitations"
    )
    roles = models.ManyToManyField(Role, blank=True, verbose_name="rôles attribués")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invitations",
        verbose_name="créé par",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        "expire le", null=True, blank=True,
        help_text="Laisser vide = pas d'expiration automatique."
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_invitations",
        verbose_name="utilisé par",
    )
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "invitation"
        verbose_name_plural = "invitations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation {self.project} ({self.token})"

    @property
    def is_valid(self):
        if self.used_by_id:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def get_accept_url(self):
        return reverse("accounts:accept_invitation", kwargs={"token": self.token})
