from django.conf import settings
from django.db import models
from django.urls import reverse


class TimeActivity(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)
    is_default = models.BooleanField("par défaut", default=False)

    class Meta:
        verbose_name = "activité"
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class TimeEntryQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Les entrées visibles selon les permissions."""
        if user.is_superuser:
            return self
        from projects.models import Project
        from core.permissions import get_user_project_permissions

        # On récupère tous les projets visibles (publics + membre)
        member_ids = Project.objects.filter(
            memberships__user=user
        ).values_list("id", flat=True)
        public_ids = Project.objects.filter(is_public=True).values_list("id", flat=True)
        all_visible = set(member_ids) | set(public_ids)

        # Les entrées propres à l'utilisateur + celles des projets où il a view_time_entries
        own = self.filter(user=user)

        # Projets où l'utilisateur a view_time_entries
        view_time_projects = []
        for pid in all_visible:
            try:
                project = Project.objects.get(pk=pid)
                perms = get_user_project_permissions(user, project)
                if "view_time_entries" in perms:
                    view_time_projects.append(pid)
            except Project.DoesNotExist:
                pass

        others = self.filter(project_id__in=view_time_projects)
        return (own | others).distinct()


class TimeEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="utilisateur",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="projet",
    )
    issue = models.ForeignKey(
        "issues.Issue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_entries",
        verbose_name="ticket",
    )
    activity = models.ForeignKey(
        TimeActivity,
        on_delete=models.PROTECT,
        verbose_name="activité",
    )
    hours = models.DecimalField(
        "heures",
        max_digits=6,
        decimal_places=2,
    )
    spent_on = models.DateField("date")
    comment = models.TextField("commentaire", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TimeEntryQuerySet.as_manager()

    class Meta:
        verbose_name = "saisie de temps"
        verbose_name_plural = "saisies de temps"
        ordering = ["-spent_on", "-created_at"]

    def __str__(self):
        return f"{self.user} – {self.hours}h – {self.spent_on}"

    def get_absolute_url(self):
        return reverse("timetracking:edit", kwargs={"pk": self.pk})

    @property
    def can_be_edited_by(self):
        """Retourne un callable : entry.can_be_edited_by(user)."""
        def check(user):
            if user.is_superuser:
                return True
            from core.permissions import get_user_project_permissions
            perms = get_user_project_permissions(user, self.project)
            return self.user == user and "log_time" in perms
        return check
