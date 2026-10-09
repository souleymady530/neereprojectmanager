from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import TemplateView, View, ListView

from core.permissions import ProjectPermissionRequiredMixin, get_user_project_permissions
from .models import WikiPage, WikiPageRevision
from .forms import WikiPageEditForm
from .services import edit_wiki_page, rollback_wiki_page
from .utils import render_markdown, diff_revisions

HOME_SLUG = "accueil"
HOME_TITLE = "Accueil"


class WikiHomeView(ProjectPermissionRequiredMixin, View):
    """Redirige vers la page d'accueil du wiki (la crée si besoin)."""
    permission_required = "view_wiki"

    def get(self, request, identifier):
        return redirect(
            reverse("projects:wiki_page", kwargs={"identifier": identifier, "slug": HOME_SLUG})
        )


class WikiPageView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "wiki/page.html"
    permission_required = "view_wiki"

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return result
        slug = kwargs.get("slug", HOME_SLUG)
        self.wiki_page = WikiPage.objects.filter(
            project=self.project, slug=slug
        ).prefetch_related("revisions").first()
        return result

    def get(self, request, *args, **kwargs):
        # Page inexistante + permission d'édition → proposer de la créer
        if self.wiki_page is None:
            user_perms = get_user_project_permissions(request.user, self.project)
            if "edit_wiki" in user_perms:
                return redirect(
                    reverse(
                        "projects:wiki_edit",
                        kwargs={"identifier": self.project.identifier, "slug": kwargs["slug"]},
                    )
                )
            raise PermissionDenied
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = self.wiki_page
        revision = page.current_revision
        html, toc = render_markdown(
            revision.content if revision else "",
            project_identifier=self.project.identifier,
        )
        ctx.update({
            "project": self.project,
            "wiki_page": page,
            "revision": revision,
            "content_html": html,
            "toc_html": toc,
            "user_perms": get_user_project_permissions(self.request.user, self.project),
            "all_pages": WikiPage.objects.filter(project=self.project).order_by("title"),
        })
        return ctx


class WikiPageEditView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "wiki/edit.html"
    permission_required = "edit_wiki"

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return result
        self.wiki_page = WikiPage.objects.filter(
            project=self.project, slug=kwargs.get("slug")
        ).first()
        return result

    def get(self, request, *args, **kwargs):
        slug = kwargs["slug"]
        page = self.wiki_page
        if page:
            rev = page.current_revision
            form = WikiPageEditForm(initial={
                "title": page.title,
                "content": rev.content if rev else "",
            })
        else:
            # Nouvelle page : on pré-remplit le titre depuis le slug
            title = slug.replace("-", " ").capitalize()
            form = WikiPageEditForm(initial={"title": title, "content": ""})
        return self.render_to_response(self._ctx(form, slug))

    def post(self, request, *args, **kwargs):
        slug = kwargs["slug"]
        form = WikiPageEditForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self._ctx(form, slug))

        page, revision = edit_wiki_page(
            project=self.project,
            user=request.user,
            title=form.cleaned_data["title"],
            content=form.cleaned_data["content"],
            comment=form.cleaned_data.get("comment", ""),
            existing_page=self.wiki_page,
        )
        messages.success(request, f"Page « {page.title} » enregistrée (v{revision.version}).")
        return redirect(page.get_absolute_url())

    def _ctx(self, form, slug):
        return {
            "project": self.project,
            "wiki_page": self.wiki_page,
            "form": form,
            "slug": slug,
            "user_perms": get_user_project_permissions(self.request.user, self.project),
        }


class WikiPageHistoryView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "wiki/history.html"
    permission_required = "view_wiki"

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return result
        self.wiki_page = get_object_or_404(
            WikiPage, project=self.project, slug=kwargs["slug"]
        )
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "project": self.project,
            "wiki_page": self.wiki_page,
            "revisions": self.wiki_page.revisions.select_related("author").order_by("-version"),
            "user_perms": get_user_project_permissions(self.request.user, self.project),
        })
        return ctx


class WikiPageRevisionView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "wiki/revision.html"
    permission_required = "view_wiki"

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return result
        self.wiki_page = get_object_or_404(
            WikiPage, project=self.project, slug=kwargs["slug"]
        )
        self.revision = get_object_or_404(
            WikiPageRevision, page=self.wiki_page, version=kwargs["version"]
        )
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        html, toc = render_markdown(
            self.revision.content,
            project_identifier=self.project.identifier,
        )
        ctx.update({
            "project": self.project,
            "wiki_page": self.wiki_page,
            "revision": self.revision,
            "content_html": html,
            "toc_html": toc,
            "user_perms": get_user_project_permissions(self.request.user, self.project),
        })
        return ctx


class WikiPageDiffView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "wiki/diff.html"
    permission_required = "view_wiki"

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return result
        self.wiki_page = get_object_or_404(
            WikiPage, project=self.project, slug=kwargs["slug"]
        )
        return result

    def get(self, request, *args, **kwargs):
        v_from = int(request.GET.get("from", 1))
        v_to = int(request.GET.get("to", self.wiki_page.version))
        self.rev_from = get_object_or_404(WikiPageRevision, page=self.wiki_page, version=v_from)
        self.rev_to = get_object_or_404(WikiPageRevision, page=self.wiki_page, version=v_to)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        diff_html = diff_revisions(
            self.rev_from.content,
            self.rev_to.content,
            old_label=f"v{self.rev_from.version}",
            new_label=f"v{self.rev_to.version}",
        )
        ctx.update({
            "project": self.project,
            "wiki_page": self.wiki_page,
            "rev_from": self.rev_from,
            "rev_to": self.rev_to,
            "diff_html": diff_html,
            "all_revisions": self.wiki_page.revisions.order_by("-version"),
            "user_perms": get_user_project_permissions(self.request.user, self.project),
        })
        return ctx


class WikiPageRollbackView(ProjectPermissionRequiredMixin, View):
    permission_required = "edit_wiki"

    def post(self, request, identifier, slug, version):
        wiki_page = get_object_or_404(WikiPage, project=self.project, slug=slug)
        target = get_object_or_404(WikiPageRevision, page=wiki_page, version=version)
        page, revision = rollback_wiki_page(wiki_page, target, request.user)
        messages.success(
            request,
            f"Page revenue à la version {target.version} (nouvelle version : {revision.version}).",
        )
        return redirect(page.get_absolute_url())


class WikiPageDeleteView(ProjectPermissionRequiredMixin, View):
    permission_required = "delete_wiki_pages"

    def post(self, request, identifier, slug):
        wiki_page = get_object_or_404(WikiPage, project=self.project, slug=slug)
        title = wiki_page.title
        wiki_page.delete()
        messages.success(request, f"Page « {title} » supprimée.")
        return redirect(
            reverse("projects:wiki_list", kwargs={"identifier": self.project.identifier})
        )


class WikiPageListView(ProjectPermissionRequiredMixin, TemplateView):
    template_name = "wiki/list.html"
    permission_required = "view_wiki"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pages = (
            WikiPage.objects.filter(project=self.project)
            .prefetch_related("revisions")
            .order_by("title")
        )
        ctx.update({
            "project": self.project,
            "pages": pages,
            "user_perms": get_user_project_permissions(self.request.user, self.project),
        })
        return ctx
