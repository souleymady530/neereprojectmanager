import json as _json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)

from core.permissions import ProjectPermissionRequiredMixin, get_user_project_permissions
from .models import Project, Membership, Role
from .forms import ProjectForm, MembershipForm


class ProjectListView(LoginRequiredMixin, ListView):
    template_name = "projects/list.html"
    context_object_name = "projects"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.filter(parent=None).prefetch_related("children")
        # Projets publics + projets dont l'utilisateur est membre
        member_projects = Project.objects.filter(memberships__user=user)
        public_projects = Project.objects.filter(is_public=True)
        return (member_projects | public_projects).filter(parent=None).distinct().prefetch_related("children")


class ProjectOverviewView(LoginRequiredMixin, DetailView):
    template_name = "projects/overview.html"
    context_object_name = "project"
    slug_field = "identifier"
    slug_url_kwarg = "identifier"

    def get_queryset(self):
        return Project.objects.prefetch_related("memberships__user", "memberships__roles")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user_perms"] = get_user_project_permissions(self.request.user, self.object)
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    form_class = ProjectForm
    template_name = "projects/form.html"

    def form_valid(self, form):
        project = form.save()
        # L'auteur devient automatiquement manager
        # JSONField __contains n'est pas supporté par SQLite → filtre Python
        default_role = next(
            (r for r in Role.objects.all() if "manage_project" in (r.permissions or [])),
            None,
        )
        membership = Membership.objects.create(user=self.request.user, project=project)
        if default_role:
            membership.roles.add(default_role)
        messages.success(self.request, f"Projet « {project.name} » créé.")
        return redirect(project.get_absolute_url())


class ProjectUpdateView(ProjectPermissionRequiredMixin, UpdateView):
    form_class = ProjectForm
    template_name = "projects/form.html"
    permission_required = "manage_project"
    slug_field = "identifier"
    slug_url_kwarg = "identifier"

    def get_queryset(self):
        return Project.objects.all()

    def get_object(self):
        return get_object_or_404(Project, identifier=self.kwargs["identifier"])

    def form_valid(self, form):
        messages.success(self.request, "Projet mis à jour.")
        return super().form_valid(form)


class ProjectSettingsView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "projects/settings.html"
    permission_required = "manage_project"

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Q
        from versions.models import Version

        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["memberships"] = self.project.memberships.select_related("user").prefetch_related("roles")
        ctx["membership_form"] = MembershipForm()

        versions = list(
            Version.objects.filter(project=self.project)
            .annotate(
                total_issues=Count("issues"),
                closed_issues=Count("issues", filter=Q(issues__status__is_closed=True)),
            )
            .order_by("status", "effective_date")
        )
        for v in versions:
            v.progress_pct = int(v.closed_issues / v.total_issues * 100) if v.total_issues else 0
        ctx["versions"] = versions
        return ctx


class MemberAddView(ProjectPermissionRequiredMixin, CreateView):
    form_class = MembershipForm
    template_name = "projects/member_form.html"
    permission_required = "manage_members"

    def form_valid(self, form):
        membership = form.save(commit=False)
        membership.project = self.project
        membership.save()
        form.save_m2m()
        messages.success(self.request, "Membre ajouté.")
        return redirect(reverse("projects:settings", kwargs={"identifier": self.project.identifier}))


class MemberRemoveView(ProjectPermissionRequiredMixin, DeleteView):
    model = Membership
    template_name = "projects/member_confirm_delete.html"
    permission_required = "manage_members"

    def get_success_url(self):
        return reverse("projects:settings", kwargs={"identifier": self.project.identifier})


class GanttView(ProjectPermissionRequiredMixin, View):
    """
    Affiche le diagramme de Gantt du projet (issues avec start_date + due_date).
    Filtres : ?tracker=<id>  ?version=<id>  ?assigned_to=<id>  ?mode=Week
    """
    permission_required = "view_issues"

    def get(self, request, identifier):
        from issues.models import Issue, Tracker
        from versions.models import Version
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # ---- filtres ----
        tracker_id  = request.GET.get("tracker", "")
        version_id  = request.GET.get("version", "")
        assigned_id = request.GET.get("assigned_to", "")
        view_mode   = request.GET.get("mode", "Week")
        if view_mode not in ("Day", "Week", "Month"):
            view_mode = "Week"

        qs = (
            Issue.objects.filter(project=self.project)
            .select_related("tracker", "status", "priority", "assigned_to")
            .order_by("start_date", "due_date")
        )
        if tracker_id:
            qs = qs.filter(tracker_id=tracker_id)
        if version_id:
            qs = qs.filter(fixed_version_id=version_id)
        if assigned_id:
            qs = qs.filter(assigned_to_id=assigned_id)

        total_count    = qs.count()
        qs_with_dates  = qs.filter(start_date__isnull=False, due_date__isnull=False)
        without_dates  = total_count - qs_with_dates.count()

        # ---- construction des tâches Frappe Gantt ----
        tasks = []
        for issue in qs_with_dates:
            start = issue.start_date
            end   = issue.due_date
            if end < start:              # données incohérentes → swap
                start, end = end, start

            # couleur via custom_class : fermé = vert, en retard = rouge, sinon bleu
            from datetime import date
            if issue.status.is_closed:
                css = "bar-done"
            elif end < date.today():
                css = "bar-overdue"
            else:
                css = "bar-open"

            tasks.append({
                "id":           str(issue.pk),
                "name":         f"#{issue.pk} {issue.subject[:60]}{'…' if len(issue.subject) > 60 else ''}",
                "start":        start.strftime("%Y-%m-%d"),
                "end":          end.strftime("%Y-%m-%d"),
                "progress":     issue.done_ratio,
                "url":          issue.get_absolute_url(),
                "custom_class": css,
            })

        # ---- données pour la barre de filtres ----
        trackers = Tracker.objects.all()
        versions = Version.objects.filter(project=self.project)
        member_ids = self.project.memberships.values_list("user_id", flat=True)
        members    = User.objects.filter(pk__in=member_ids)

        return render(request, "projects/gantt.html", {
            "project":        self.project,
            "user_perms":     get_user_project_permissions(request.user, self.project),
            "tasks_json":     _json.dumps(tasks, ensure_ascii=False),
            "task_count":     len(tasks),
            "without_dates":  without_dates,
            "view_mode":      view_mode,
            "trackers":       trackers,
            "versions":       versions,
            "members":        members,
            "current_tracker":  tracker_id,
            "current_version":  version_id,
            "current_assigned": assigned_id,
        })
