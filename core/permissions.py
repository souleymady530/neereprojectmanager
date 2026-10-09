"""
Couche de permissions orientée projet.

Usage dans les vues :
    class MyView(ProjectPermissionRequiredMixin, View):
        permission_required = "edit_issues"

Usage dans le code :
    if user.has_project_permission(project, "add_issues"):
        ...

Codes de permission disponibles :
    view_issues, add_issues, edit_issues, delete_issues,
    log_time, view_time_entries,
    manage_members, manage_versions,
    manage_project
"""

from functools import wraps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


def get_user_project_permissions(user, project):
    """
    Retourne l'ensemble des codes de permission de l'utilisateur
    dans le projet donné. Résultat mis en cache sur la requête.
    """
    if user.is_superuser:
        return _all_permissions()

    cache_attr = "_project_perms_cache"
    if not hasattr(user, cache_attr):
        setattr(user, cache_attr, {})

    cache = getattr(user, cache_attr)
    project_pk = project.pk

    if project_pk not in cache:
        from projects.models import Membership
        try:
            membership = Membership.objects.get(user=user, project=project)
            perms = set()
            for role in membership.roles.all():
                perms.update(role.permissions)
            cache[project_pk] = perms
        except Membership.DoesNotExist:
            # Projet public : permission de lecture uniquement
            if project.is_public:
                cache[project_pk] = {"view_issues"}
            else:
                cache[project_pk] = set()

    return cache[project_pk]


def _all_permissions():
    return {
        "view_issues", "add_issues", "edit_issues", "delete_issues",
        "log_time", "view_time_entries",
        "manage_members", "manage_versions", "manage_project",
        "view_wiki", "edit_wiki", "delete_wiki_pages",
    }


class ProjectPermissionRequiredMixin(LoginRequiredMixin):
    """
    Mixin pour les vues qui nécessitent une permission sur un projet.
    Le projet est récupéré via self.get_project() ou via le kwarg `identifier`.
    """
    permission_required: str = ""

    def get_project(self):
        from projects.models import Project
        identifier = self.kwargs.get("identifier")
        return get_object_or_404(Project, identifier=identifier)

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # super() gère la redirection si non connecté
        if not request.user.is_authenticated:
            return response

        project = self.get_project()
        self.project = project

        if self.permission_required:
            perms = get_user_project_permissions(request.user, project)
            if self.permission_required not in perms:
                raise PermissionDenied
        return response
