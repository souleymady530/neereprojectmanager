import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from .models import Report, COLUMN_LABELS
from .forms import ReportForm
from issues.models import Issue


class ReportListView(LoginRequiredMixin, ListView):
    template_name = "reports/list.html"
    context_object_name = "reports"

    def get_queryset(self):
        return Report.objects.filter(owner=self.request.user).select_related("project")


class ReportCreateView(LoginRequiredMixin, CreateView):
    template_name = "reports/form.html"
    form_class = ReportForm

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Rapport créé.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "title": "Nouveau rapport"}


class ReportUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "reports/form.html"
    form_class = ReportForm

    def get_queryset(self):
        return Report.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        messages.success(self.request, "Rapport mis à jour.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "title": f"Modifier « {self.object.name} »"}


class ReportDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "reports/confirm_delete.html"
    success_url = reverse_lazy("reports:list")

    def get_queryset(self):
        return Report.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Rapport supprimé.")
        return super().form_valid(form)


class ReportDetailView(LoginRequiredMixin, DetailView):
    template_name = "reports/detail.html"

    def get_queryset(self):
        return Report.objects.filter(owner=self.request.user).select_related("project")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        report = self.object
        qs = _run_report(report, self.request.user)
        ctx["issues"] = qs
        ctx["total"] = qs.count()
        ctx["column_labels"] = [(col, COLUMN_LABELS.get(col, col)) for col in report.columns]
        ctx["filter_summary"] = _filter_summary(report.filters)
        return ctx


class ReportExportCSVView(LoginRequiredMixin, View):
    def get(self, request, pk):
        report = Report.objects.filter(owner=request.user).get(pk=pk)
        qs = _run_report(report, request.user)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="rapport_{report.pk}.csv"'
        response.write("\ufeff")  # BOM pour Excel
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["#"] + [COLUMN_LABELS.get(c, c) for c in report.columns])
        for issue in qs:
            writer.writerow([issue.pk] + [_col_value(issue, c) for c in report.columns])
        return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_report(report, user):
    qs = (
        Issue.objects.visible_to(user)
        .select_related("tracker", "status", "priority", "assigned_to",
                        "fixed_version", "project", "author")
    )
    if report.project:
        qs = qs.filter(project=report.project)
    f = report.filters
    if f.get("subject"):
        qs = qs.filter(subject__icontains=f["subject"])
    if f.get("tracker"):
        qs = qs.filter(tracker_id__in=f["tracker"])
    if f.get("status"):
        qs = qs.filter(status_id__in=f["status"])
    if f.get("priority"):
        qs = qs.filter(priority_id__in=f["priority"])
    if f.get("assigned_to"):
        qs = qs.filter(assigned_to_id=f["assigned_to"])
    if f.get("fixed_version"):
        qs = qs.filter(fixed_version_id=f["fixed_version"])
    if f.get("open_only"):
        qs = qs.filter(status__is_closed=False)
    if "is_evaluated" in f:
        qs = qs.filter(is_evaluated=f["is_evaluated"])
    if f.get("start_date_after"):
        qs = qs.filter(start_date__gte=f["start_date_after"])
    if f.get("start_date_before"):
        qs = qs.filter(start_date__lte=f["start_date_before"])
    if f.get("due_date_after"):
        qs = qs.filter(due_date__gte=f["due_date_after"])
    if f.get("due_date_before"):
        qs = qs.filter(due_date__lte=f["due_date_before"])
    return qs.order_by("-updated_at")


def _col_value(issue, col):
    mapping = {
        "subject": lambda i: i.subject,
        "tracker": lambda i: str(i.tracker),
        "status": lambda i: str(i.status),
        "priority": lambda i: str(i.priority),
        "assigned_to": lambda i: str(i.assigned_to) if i.assigned_to else "",
        "fixed_version": lambda i: str(i.fixed_version) if i.fixed_version else "",
        "project": lambda i: str(i.project),
        "start_date": lambda i: str(i.start_date) if i.start_date else "",
        "due_date": lambda i: str(i.due_date) if i.due_date else "",
        "estimated_hours": lambda i: str(i.estimated_hours) if i.estimated_hours else "",
        "done_ratio": lambda i: f"{i.done_ratio}%",
        "is_evaluated": lambda i: "Oui" if i.is_evaluated else "Non",
        "author": lambda i: str(i.author) if i.author else "",
        "created_at": lambda i: i.created_at.strftime("%d/%m/%Y %H:%M"),
        "updated_at": lambda i: i.updated_at.strftime("%d/%m/%Y %H:%M"),
    }
    return mapping.get(col, lambda i: "")(issue)


def _filter_summary(filters):
    """Retourne une liste lisible des filtres actifs."""
    from issues.models import Tracker, IssueStatus, IssuePriority
    from django.contrib.auth import get_user_model
    from versions.models import Version
    User = get_user_model()
    parts = []
    if filters.get("subject"):
        parts.append(f"Sujet contient « {filters['subject']} »")
    if filters.get("tracker"):
        names = ", ".join(Tracker.objects.filter(pk__in=filters["tracker"]).values_list("name", flat=True))
        parts.append(f"Tracker : {names}")
    if filters.get("status"):
        names = ", ".join(IssueStatus.objects.filter(pk__in=filters["status"]).values_list("name", flat=True))
        parts.append(f"Statut : {names}")
    if filters.get("priority"):
        names = ", ".join(IssuePriority.objects.filter(pk__in=filters["priority"]).values_list("name", flat=True))
        parts.append(f"Priorité : {names}")
    if filters.get("assigned_to"):
        try:
            u = User.objects.get(pk=filters["assigned_to"])
            parts.append(f"Assigné à : {u.get_full_name() or u.username}")
        except User.DoesNotExist:
            pass
    if filters.get("fixed_version"):
        try:
            v = Version.objects.get(pk=filters["fixed_version"])
            parts.append(f"Version : {v}")
        except Version.DoesNotExist:
            pass
    if filters.get("open_only"):
        parts.append("Tickets ouverts seulement")
    if "is_evaluated" in filters:
        parts.append(f"Évalué : {'Oui' if filters['is_evaluated'] else 'Non'}")
    if filters.get("start_date_after"):
        parts.append(f"Début après le {filters['start_date_after']}")
    if filters.get("start_date_before"):
        parts.append(f"Début avant le {filters['start_date_before']}")
    if filters.get("due_date_after"):
        parts.append(f"Échéance après le {filters['due_date_after']}")
    if filters.get("due_date_before"):
        parts.append(f"Échéance avant le {filters['due_date_before']}")
    return parts
