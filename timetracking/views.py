from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncWeek
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView

from core.htmx import is_htmx
from core.permissions import ProjectPermissionRequiredMixin, get_user_project_permissions
from projects.models import Project
from issues.models import Issue
from .models import TimeEntry, TimeActivity
from .forms import TimeEntryForm
from .filters import TimeEntryFilter


class TimeEntryListView(ProjectPermissionRequiredMixin, ListView):
    """Liste des saisies de temps d'un projet avec totaux."""
    template_name = "timetracking/list.html"
    context_object_name = "entries"
    paginate_by = 50
    permission_required = "view_time_entries"

    def get_queryset(self):
        qs = (
            TimeEntry.objects.filter(project=self.project)
            .select_related("user", "activity", "issue")
            .order_by("-spent_on", "-created_at")
        )
        self.filter = TimeEntryFilter(self.request.GET, queryset=qs)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        ctx["filter"] = self.filter
        ctx["user_perms"] = get_user_project_permissions(self.request.user, self.project)
        # Total de la sélection filtrée
        ctx["total_hours"] = self.filter.qs.aggregate(t=Sum("hours"))["t"] or 0
        return ctx


class TimeEntryCreateView(ProjectPermissionRequiredMixin, CreateView):
    """Saisir du temps sur un projet (ticket optionnel)."""
    form_class = TimeEntryForm
    template_name = "timetracking/form.html"
    permission_required = "log_time"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["project"] = self.project
        return kw

    def get_initial(self):
        initial = super().get_initial()
        # Pré-remplir le ticket si passé en GET
        issue_pk = self.request.GET.get("issue")
        if issue_pk:
            try:
                initial["issue"] = Issue.objects.get(pk=issue_pk, project=self.project)
            except Issue.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        entry = form.save(commit=False)
        entry.user = self.request.user
        entry.project = self.project
        entry.save()
        messages.success(self.request, f"{entry.hours}h saisie(s) le {entry.spent_on}.")
        # Retour vers le ticket si la saisie en venait
        if entry.issue:
            return redirect(entry.issue.get_absolute_url())
        return redirect(
            reverse("projects:time_entries", kwargs={"identifier": self.project.identifier})
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        return ctx


class TimeEntryUpdateView(LoginRequiredMixin, UpdateView):
    """Modifier une saisie de temps (propriétaire uniquement ou superuser)."""
    form_class = TimeEntryForm
    template_name = "timetracking/form.html"

    def get_object(self):
        entry = get_object_or_404(TimeEntry, pk=self.kwargs["pk"])
        user = self.request.user
        if not user.is_superuser and entry.user != user:
            raise PermissionDenied
        return entry

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["project"] = self.object.project
        return kw

    def form_valid(self, form):
        entry = form.save()
        messages.success(self.request, "Saisie mise à jour.")
        if entry.issue:
            return redirect(entry.issue.get_absolute_url())
        return redirect(
            reverse("projects:time_entries", kwargs={"identifier": entry.project.identifier})
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.object.project
        return ctx


class TimeEntryDeleteView(LoginRequiredMixin, DeleteView):
    """Supprimer une saisie (propriétaire ou superuser)."""
    model = TimeEntry
    template_name = "timetracking/confirm_delete.html"

    def get_object(self):
        entry = get_object_or_404(TimeEntry, pk=self.kwargs["pk"])
        if not self.request.user.is_superuser and entry.user != self.request.user:
            raise PermissionDenied
        return entry

    def get_success_url(self):
        messages.success(self.request, "Saisie supprimée.")
        return reverse(
            "projects:time_entries",
            kwargs={"identifier": self.object.project.identifier},
        )

    def form_valid(self, form):
        """Supporte aussi la suppression via HTMX (réponse vide 200)."""
        self.object = self.get_object()
        project_identifier = self.object.project.identifier
        self.object.delete()
        if is_htmx(self.request):
            from django.http import HttpResponse
            return HttpResponse(status=200)
        messages.success(self.request, "Saisie supprimée.")
        return redirect(reverse("projects:time_entries", kwargs={"identifier": project_identifier}))


class TimeReportView(ProjectPermissionRequiredMixin, TemplateView):
    """Rapport agrégé : totaux par utilisateur, activité et mois."""
    template_name = "timetracking/report.html"
    permission_required = "view_time_entries"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.project

        base_qs = TimeEntry.objects.filter(project=project)

        # Filtres date depuis GET
        date_from = self.request.GET.get("from")
        date_to = self.request.GET.get("to")
        if date_from:
            base_qs = base_qs.filter(spent_on__gte=date_from)
        if date_to:
            base_qs = base_qs.filter(spent_on__lte=date_to)

        # Total global
        total = base_qs.aggregate(t=Sum("hours"))["t"] or 0

        # Par utilisateur
        by_user = (
            base_qs.values("user__id", "user__first_name", "user__last_name", "user__username")
            .annotate(total=Sum("hours"))
            .order_by("-total")
        )
        for row in by_user:
            full = f"{row['user__first_name']} {row['user__last_name']}".strip()
            row["display_name"] = full or row["user__username"]

        # Par activité
        by_activity = (
            base_qs.values("activity__name")
            .annotate(total=Sum("hours"))
            .order_by("-total")
        )

        # Par version
        by_version = (
            base_qs.filter(issue__fixed_version__isnull=False)
            .values("issue__fixed_version__name")
            .annotate(total=Sum("hours"))
            .order_by("-total")
        )

        # Par mois (12 derniers mois)
        by_month = (
            base_qs.annotate(month=TruncMonth("spent_on"))
            .values("month")
            .annotate(total=Sum("hours"))
            .order_by("month")
        )

        ctx.update({
            "project": project,
            "user_perms": get_user_project_permissions(self.request.user, project),
            "total": total,
            "by_user": list(by_user),
            "by_activity": list(by_activity),
            "by_version": list(by_version),
            "by_month": list(by_month),
            "date_from": date_from or "",
            "date_to": date_to or "",
        })
        return ctx
