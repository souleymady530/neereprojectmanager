from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DetailView, CreateView, UpdateView, View, ListView

from core.permissions import ProjectPermissionRequiredMixin, get_user_project_permissions
from core.htmx import is_htmx
from .models import Issue, IssueStatus, Journal, Watcher
from .forms import IssueForm, JournalNoteForm, StatusUpdateForm, DoneRatioUpdateForm
from .filters import IssueFilter
from .services import update_issue


class IssueListView(LoginRequiredMixin, ListView):
    template_name = "issues/list.html"
    context_object_name = "issues"
    paginate_by = 25

    def get_queryset(self):
        from projects.models import Project
        identifier = self.kwargs.get("identifier")
        if identifier:
            self.project = get_object_or_404(Project, identifier=identifier)
            qs = Issue.objects.filter(project=self.project)
        else:
            self.project = None
            qs = Issue.objects.visible_to(self.request.user)

        qs = qs.select_related(
            "tracker", "status", "priority", "assigned_to", "project"
        ).order_by("-updated_at")

        self.filter = IssueFilter(self.request.GET, queryset=qs)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filter
        ctx["project"] = getattr(self, "project", None)
        return ctx


class IssueDetailView(LoginRequiredMixin, DetailView):
    template_name = "issues/detail.html"
    context_object_name = "issue"

    def get_queryset(self):
        return Issue.objects.visible_to(self.request.user).select_related(
            "project", "tracker", "status", "priority", "author",
            "assigned_to", "fixed_version", "parent",
        ).prefetch_related("journals__details", "journals__user", "children")

    def get_context_data(self, **kwargs):
        from django.db.models import Sum
        from timetracking.models import TimeEntry
        from customfields.utils import get_display_values
        ctx = super().get_context_data(**kwargs)
        ctx["note_form"] = JournalNoteForm()
        ctx["user_perms"] = get_user_project_permissions(self.request.user, self.object.project)
        ctx["allowed_statuses"] = self.object.allowed_statuses_for(self.request.user)
        ctx["is_watching"] = Watcher.objects.filter(
            issue=self.object, user=self.request.user
        ).exists()
        ctx["custom_field_values"] = get_display_values(self.object)
        # Temps saisi sur ce ticket
        time_qs = TimeEntry.objects.filter(issue=self.object).select_related("user", "activity")
        ctx["time_entries"] = time_qs.order_by("-spent_on")[:5]
        ctx["total_hours"] = time_qs.aggregate(t=Sum("hours"))["t"] or 0
        return ctx


class IssueCreateView(ProjectPermissionRequiredMixin, CreateView):
    form_class = IssueForm
    template_name = "issues/form.html"
    permission_required = "add_issues"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["project"] = self.project
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        from notifications.emails import notify_issue_created
        from customfields.utils import save_custom_values
        issue = form.save(commit=False)
        issue.project = self.project
        issue.author = self.request.user
        if not issue.status_id and issue.tracker.default_status:
            issue.status = issue.tracker.default_status
        issue.save()
        save_custom_values(issue, form.cleaned_data, form._applicable_custom_fields)
        notify_issue_created(issue, actor=self.request.user)
        messages.success(self.request, f"Ticket #{issue.pk} créé.")
        return redirect(issue.get_absolute_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        return ctx


class IssueUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "issues/form.html"
    form_class = IssueForm

    def get_queryset(self):
        return Issue.objects.visible_to(self.request.user)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["project"] = self.object.project
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        from notifications.emails import notify_issue_updated
        from customfields.utils import save_custom_values
        from issues.models import JournalDetail
        journal = update_issue(
            issue=self.object,
            user=self.request.user,
            data=form.cleaned_data,
            note=form.cleaned_data.get("_note", ""),
        )
        cf_changes = save_custom_values(
            self.object, form.cleaned_data, form._applicable_custom_fields
        )
        # Journal the custom-field changes (attach to existing journal or create one)
        if cf_changes:
            if journal is None:
                journal = Journal.objects.create(
                    issue=self.object, user=self.request.user, notes=""
                )
            JournalDetail.objects.bulk_create([
                JournalDetail(
                    journal=journal,
                    field=f"cf_{cf.pk}",
                    old_value=old or None,
                    new_value=new or None,
                )
                for cf, old, new in cf_changes
            ])
        notify_issue_updated(self.object, journal, actor=self.request.user)
        messages.success(self.request, "Ticket mis à jour.")
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.object.project
        return ctx


class IssueAddNoteView(LoginRequiredMixin, View):
    """Ajouter un commentaire. Retourne un partial HTMX ou redirige."""

    def post(self, request, pk):
        issue = get_object_or_404(Issue.objects.visible_to(request.user), pk=pk)
        form = JournalNoteForm(request.POST)

        if form.is_valid() and form.cleaned_data["notes"].strip():
            from notifications.emails import notify_issue_commented
            journal = Journal.objects.create(
                issue=issue,
                user=request.user,
                notes=form.cleaned_data["notes"],
            )
            notify_issue_commented(issue, journal, actor=request.user)
            if is_htmx(request):
                return render(request, "issues/_journal_entry.html", {"journal": journal})

        if is_htmx(request):
            # Note vide ou invalide : rien à insérer, réponse vide 204
            from django.http import HttpResponse
            return HttpResponse(status=204)

        return redirect(issue.get_absolute_url())


class IssueStatusUpdateView(LoginRequiredMixin, View):
    """Changer le statut d'un ticket. Retourne le widget _status_widget.html via HTMX."""

    def post(self, request, pk):
        issue = get_object_or_404(Issue.objects.visible_to(request.user), pk=pk)
        user_perms = get_user_project_permissions(request.user, issue.project)

        if "edit_issues" not in user_perms:
            raise PermissionDenied

        allowed = issue.allowed_statuses_for(request.user)
        form = StatusUpdateForm(request.POST, allowed_statuses=allowed)

        if form.is_valid():
            new_status = form.cleaned_data["status_id"]
            update_issue(issue, request.user, {"status": new_status})
            issue.refresh_from_db()

        # Recalculer allowed après la mise à jour
        allowed = issue.allowed_statuses_for(request.user)

        if is_htmx(request):
            return render(request, "issues/_status_widget.html", {
                "issue": issue,
                "allowed_statuses": allowed,
                "user_perms": user_perms,
            })
        return redirect(issue.get_absolute_url())


class IssueDoneRatioUpdateView(LoginRequiredMixin, View):
    """Changer l'avancement d'un ticket. Retourne le widget _done_ratio_widget.html via HTMX."""

    def post(self, request, pk):
        issue = get_object_or_404(Issue.objects.visible_to(request.user), pk=pk)
        user_perms = get_user_project_permissions(request.user, issue.project)

        if "edit_issues" not in user_perms:
            raise PermissionDenied

        form = DoneRatioUpdateForm(request.POST)
        if form.is_valid():
            update_issue(issue, request.user, {"done_ratio": form.cleaned_data["done_ratio"]})
            issue.refresh_from_db()

        if is_htmx(request):
            return render(request, "issues/_done_ratio_widget.html", {
                "issue": issue,
                "user_perms": user_perms,
            })
        return redirect(issue.get_absolute_url())


class IssueWatchToggleView(LoginRequiredMixin, View):
    """Surveiller / cesser de surveiller un ticket. Retourne le partial _watch_button.html via HTMX."""

    def post(self, request, pk):
        issue = get_object_or_404(Issue.objects.visible_to(request.user), pk=pk)
        watcher, created = Watcher.objects.get_or_create(issue=issue, user=request.user)
        if not created:
            watcher.delete()
            is_watching = False
        else:
            is_watching = True

        if is_htmx(request):
            return render(request, "issues/_watch_button.html", {
                "issue": issue,
                "is_watching": is_watching,
            })
        return redirect(issue.get_absolute_url())


class KanbanView(LoginRequiredMixin, View):
    """Tableau Kanban : colonnes = statuts ouverts, cartes = tickets."""

    template_name = "issues/kanban.html"

    def get(self, request, identifier=None):
        from projects.models import Project

        if identifier:
            project = get_object_or_404(Project, identifier=identifier)
            qs = Issue.objects.filter(project=project)
            user_perms = get_user_project_permissions(request.user, project)
        else:
            project = None
            qs = Issue.objects.visible_to(request.user)
            user_perms = set()

        statuses = list(IssueStatus.objects.order_by("position"))

        qs = qs.select_related(
            "tracker", "status", "priority", "assigned_to", "project"
        ).order_by("priority__position", "-updated_at")

        f = IssueFilter(request.GET, queryset=qs)
        filtered_qs = list(f.qs)

        columns = {s.pk: [] for s in statuses}
        for issue in filtered_qs:
            if issue.status_id in columns:
                columns[issue.status_id].append(issue)

        from datetime import date
        return render(request, self.template_name, {
            "project": project,
            "statuses": statuses,
            "columns": columns,
            "filter": f,
            "user_perms": user_perms,
            "total": len(filtered_qs),
            "today": date.today(),
        })


class KanbanMoveView(LoginRequiredMixin, View):
    """Déplacer une carte Kanban vers un nouveau statut (appelé en JS fetch)."""

    def post(self, request, pk):
        issue = get_object_or_404(Issue.objects.visible_to(request.user), pk=pk)
        user_perms = get_user_project_permissions(request.user, issue.project)

        if "edit_issues" not in user_perms:
            return JsonResponse({"ok": False, "error": "Permission refusée"}, status=403)

        status_id = request.POST.get("status_id")
        try:
            new_status = IssueStatus.objects.get(pk=status_id)
        except IssueStatus.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Statut introuvable"}, status=400)

        allowed = issue.allowed_statuses_for(request.user)
        if new_status not in allowed and not request.user.is_superuser:
            return JsonResponse({"ok": False, "error": "Transition non autorisée"}, status=403)

        update_issue(issue, request.user, {"status": new_status})
        return JsonResponse({"ok": True, "status_name": new_status.name})
