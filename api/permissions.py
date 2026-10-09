"""
Permissions DRF qui s'appuient sur le système de rôles projet existant.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.permissions import get_user_project_permissions


def _project_from_obj(obj):
    """Essaie de retrouver l'objet Project depuis n'importe quel modèle du domaine."""
    if hasattr(obj, "project"):
        return obj.project
    return obj  # obj IS the project


class ProjectReadPermission(BasePermission):
    """
    Lecture autorisée si le projet est public ou si l'utilisateur est membre.
    """
    message = "Vous n'avez pas accès à ce projet."

    def has_object_permission(self, request, view, obj):
        project = _project_from_obj(obj)
        if project.is_public:
            return True
        from projects.models import Membership
        return Membership.objects.filter(user=request.user, project=project).exists()


class HasProjectPerm(BasePermission):
    """
    Usage : set `required_perms` on the ViewSet.

    Lit/Écrit nécessite l'une des permissions requises selon la méthode HTTP.
    La convention :
        read_perms  = permissions pour SAFE_METHODS
        write_perms = permissions pour les autres méthodes
    Si l'attribut n'est pas défini, la permission est accordée.
    """
    message = "Permission insuffisante pour cette action."

    def _check(self, request, view, obj):
        project = _project_from_obj(obj)
        perms = get_user_project_permissions(request.user, project)

        if request.method in SAFE_METHODS:
            required = getattr(view, "read_perms", [])
        else:
            required = getattr(view, "write_perms", [])

        if not required:
            return True
        return any(p in perms for p in required)

    def has_object_permission(self, request, view, obj):
        return self._check(request, view, obj)
