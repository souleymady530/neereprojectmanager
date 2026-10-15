from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from issues.models import Issue
from projects.models import Project
from wiki.models import WikiPage


class SearchView(LoginRequiredMixin, TemplateView):
    template_name = "core/search_results.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        ctx["q"] = q

        if len(q) < 2:
            ctx["issues"] = []
            ctx["projects"] = []
            ctx["wiki_pages"] = []
            return ctx

        # Projets visibles
        if self.request.user.is_superuser:
            visible_projects = Project.objects.filter(status="active")
        else:
            member_ids = self.request.user.memberships.values_list("project_id", flat=True)
            visible_projects = Project.objects.filter(
                Q(pk__in=member_ids) | Q(is_public=True), status="active"
            )

        # Tickets
        issues = (
            Issue.objects.visible_to(self.request.user)
            .filter(Q(subject__icontains=q) | Q(description__icontains=q))
            .select_related("project", "status", "priority", "tracker")
            .order_by("-updated_at")[:20]
        )

        # Projets
        projects = visible_projects.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )[:10]

        # Wiki
        wiki_pages = (
            WikiPage.objects.filter(
                project__in=visible_projects,
                is_redirect=False,
            )
            .filter(Q(title__icontains=q) | Q(content__icontains=q))
            .select_related("project")
            .order_by("-updated_at")[:10]
        )

        ctx["issues"] = issues
        ctx["projects"] = projects
        ctx["wiki_pages"] = wiki_pages
        ctx["total"] = len(issues) + len(projects) + len(wiki_pages)
        return ctx
