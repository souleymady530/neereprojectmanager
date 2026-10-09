from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, DeleteView, TemplateView

from core.permissions import ProjectPermissionRequiredMixin, get_user_project_permissions
from issues.models import Issue
from projects.models import Project
from .models import Version
from .forms import VersionForm


class RoadmapView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "versions/roadmap.html"
    permission_required = "view_issues"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.project

        # Versions avec compteurs (une seule requête)
        versions = list(
            Version.objects.filter(project=project)
            .annotate(
                total_issues=Count("issues"),
                closed_issues=Count("issues", filter=Q(issues__status__is_closed=True)),
            )
            .order_by(
                # Ouverte d'abord, puis verrouillée, puis fermée
                "status",
                "effective_date",
                "name",
            )
        )

        # Calcul du pourcentage côté Python (évite un ExpressionWrapper complexe)
        for v in versions:
            v.progress_pct = (
                int(v.closed_issues / v.total_issues * 100) if v.total_issues else 0
            )

        # Tickets ouverts par version (une seule requête pour toutes les versions)
        version_ids = [v.pk for v in versions]
        open_issues = list(
            Issue.objects.filter(
                project=project,
                fixed_version_id__in=version_ids,
                status__is_closed=False,
            )
            .select_related("tracker", "status", "priority", "assigned_to")
            .order_by("priority__position", "due_date", "pk")
        )

        # Regroupement en mémoire
        issues_by_version = {}
        for issue in open_issues:
            issues_by_version.setdefault(issue.fixed_version_id, []).append(issue)

        for v in versions:
            v.open_issues_list = issues_by_version.get(v.pk, [])

        # Backlog : tickets ouverts sans version
        backlog = list(
            Issue.objects.filter(
                project=project,
                fixed_version__isnull=True,
                status__is_closed=False,
            )
            .select_related("tracker", "status", "priority", "assigned_to")
            .order_by("priority__position", "due_date", "pk")
        )

        ctx["project"] = project
        ctx["versions"] = versions
        ctx["backlog"] = backlog
        ctx["user_perms"] = get_user_project_permissions(self.request.user, project)
        return ctx


class VersionCreateView(ProjectPermissionRequiredMixin, CreateView):
    form_class = VersionForm
    template_name = "versions/form.html"
    permission_required = "manage_versions"

    def form_valid(self, form):
        version = form.save(commit=False)
        version.project = self.project
        version.save()
        messages.success(self.request, f"Version « {version.name} » créée.")
        return redirect(reverse("projects:roadmap", kwargs={"identifier": self.project.identifier}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        return ctx


class VersionUpdateView(ProjectPermissionRequiredMixin, UpdateView):
    form_class = VersionForm
    template_name = "versions/form.html"
    permission_required = "manage_versions"

    def get_object(self):
        return get_object_or_404(Version, pk=self.kwargs["pk"], project=self.project)

    def form_valid(self, form):
        messages.success(self.request, "Version mise à jour.")
        return redirect(reverse("projects:roadmap", kwargs={"identifier": self.project.identifier}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        return ctx


class VersionDeleteView(ProjectPermissionRequiredMixin, DeleteView):
    model = Version
    template_name = "versions/confirm_delete.html"
    permission_required = "manage_versions"

    def get_object(self):
        return get_object_or_404(Version, pk=self.kwargs["pk"], project=self.project)

    def get_success_url(self):
        messages.success(self.request, "Version supprimée.")
        return reverse("projects:roadmap", kwargs={"identifier": self.project.identifier})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        return ctx
