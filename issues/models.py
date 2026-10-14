from django.conf import settings
from django.db import models
from django.urls import reverse


class Tracker(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)
    default_status = models.ForeignKey(
        "IssueStatus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="statut par défaut",
    )

    class Meta:
        verbose_name = "tracker"
        ordering = ["position"]

    def __str__(self):
        return self.name


class IssueStatus(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    is_closed = models.BooleanField("fermé", default=False)
    position = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "statut"
        verbose_name_plural = "statuts"
        ordering = ["position"]

    def __str__(self):
        return self.name


class IssuePriority(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)
    is_default = models.BooleanField("par défaut", default=False)
    color = models.CharField("couleur CSS", max_length=20, default="#888888")

    class Meta:
        verbose_name = "priorité"
        ordering = ["position"]

    def __str__(self):
        return self.name


class WorkflowTransition(models.Model):
    """Définit quels statuts un rôle peut atteindre depuis un statut donné pour un tracker."""
    tracker = models.ForeignKey(Tracker, on_delete=models.CASCADE, related_name="transitions")
    role = models.ForeignKey("projects.Role", on_delete=models.CASCADE, related_name="transitions")
    old_status = models.ForeignKey(
        IssueStatus, on_delete=models.CASCADE, related_name="transitions_from"
    )
    new_status = models.ForeignKey(
        IssueStatus, on_delete=models.CASCADE, related_name="transitions_to"
    )

    class Meta:
        verbose_name = "transition de workflow"
        unique_together = [("tracker", "role", "old_status", "new_status")]

    def __str__(self):
        return f"{self.tracker} | {self.role}: {self.old_status} → {self.new_status}"


class IssueQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Filtre les tickets accessibles à un utilisateur."""
        if user.is_superuser:
            return self
        from projects.models import Project
        member_project_ids = Project.objects.filter(
            memberships__user=user
        ).values_list("id", flat=True)
        public_project_ids = Project.objects.filter(
            is_public=True
        ).values_list("id", flat=True)
        visible_ids = set(member_project_ids) | set(public_project_ids)
        return self.filter(project_id__in=visible_ids)

    def open(self):
        return self.filter(status__is_closed=False)

    def closed(self):
        return self.filter(status__is_closed=True)


class Issue(models.Model):
    DONE_RATIO_CHOICES = [(i, f"{i}%") for i in range(0, 101, 10)]

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="issues"
    )
    tracker = models.ForeignKey(Tracker, on_delete=models.PROTECT)
    subject = models.CharField("sujet", max_length=255)
    description = models.TextField("description", blank=True)
    status = models.ForeignKey(IssueStatus, on_delete=models.PROTECT)
    priority = models.ForeignKey(IssuePriority, on_delete=models.PROTECT)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_issues",
        verbose_name="auteur",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_issues",
        verbose_name="assigné à",
    )
    fixed_version = models.ForeignKey(
        "versions.Version",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues",
        verbose_name="version cible",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="ticket parent",
    )
    start_date = models.DateField("date de début", null=True, blank=True)
    due_date = models.DateField("date d'échéance", null=True, blank=True)
    estimated_hours = models.DecimalField(
        "heures estimées", max_digits=6, decimal_places=2, null=True, blank=True
    )
    done_ratio = models.PositiveSmallIntegerField(
        "avancement (%)", choices=DONE_RATIO_CHOICES, default=0
    )
    is_evaluated = models.BooleanField("évalué", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = IssueQuerySet.as_manager()

    class Meta:
        verbose_name = "ticket"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.subject}"

    def get_absolute_url(self):
        return reverse("issues:detail", kwargs={"pk": self.pk})

    @property
    def git_branch(self):
        prefix = self.project.issue_prefix.strip().upper() if self.project.issue_prefix else self.project.identifier.upper()
        return f"{prefix}-{self.pk}"

    def allowed_statuses_for(self, user):
        """Retourne les statuts vers lesquels l'utilisateur peut transitionner."""
        from projects.models import Membership
        try:
            membership = Membership.objects.get(user=user, project=self.project)
            role_ids = membership.roles.values_list("id", flat=True)
        except Membership.DoesNotExist:
            return IssueStatus.objects.none()

        allowed_ids = WorkflowTransition.objects.filter(
            tracker=self.tracker,
            role_id__in=role_ids,
            old_status=self.status,
        ).values_list("new_status_id", flat=True)

        return IssueStatus.objects.filter(pk__in=allowed_ids)


class Journal(models.Model):
    """Entrée d'historique : note et/ou modifications d'un ticket."""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="journals")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    notes = models.TextField("note", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "journal"
        ordering = ["created_at"]

    def __str__(self):
        return f"Journal #{self.pk} de #{self.issue_id}"


class JournalDetail(models.Model):
    """Détail d'une modification dans un journal."""
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="details")
    field = models.CharField("champ", max_length=100)
    old_value = models.TextField("ancienne valeur", blank=True, null=True)
    new_value = models.TextField("nouvelle valeur", blank=True, null=True)

    class Meta:
        verbose_name = "détail de journal"

    def __str__(self):
        return f"{self.field}: {self.old_value} → {self.new_value}"


class IssueRelation(models.Model):
    TYPE_RELATES = "relates"
    TYPE_BLOCKS = "blocks"
    TYPE_BLOCKED = "blocked_by"
    TYPE_PRECEDES = "precedes"
    TYPE_FOLLOWS = "follows"
    TYPE_DUPLICATES = "duplicates"
    TYPE_DUPLICATED = "duplicated_by"

    RELATION_TYPES = [
        (TYPE_RELATES, "lié à"),
        (TYPE_BLOCKS, "bloque"),
        (TYPE_BLOCKED, "bloqué par"),
        (TYPE_PRECEDES, "précède"),
        (TYPE_FOLLOWS, "suit"),
        (TYPE_DUPLICATES, "duplique"),
        (TYPE_DUPLICATED, "dupliqué par"),
    ]

    issue_from = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="relations_from")
    issue_to = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="relations_to")
    relation_type = models.CharField("type", max_length=20, choices=RELATION_TYPES, default=TYPE_RELATES)

    class Meta:
        verbose_name = "relation"
        unique_together = [("issue_from", "issue_to", "relation_type")]

    def __str__(self):
        return f"#{self.issue_from_id} {self.get_relation_type_display()} #{self.issue_to_id}"


class Watcher(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="watchers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("issue", "user")]
