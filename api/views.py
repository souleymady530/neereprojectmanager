from django.contrib.auth import get_user_model
from django.db.models import Q as models_Q
from rest_framework import viewsets, mixins, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from projects.models import Project, Membership
from issues.models import Issue, IssueStatus, IssuePriority, Tracker, Journal
from versions.models import Version
from timetracking.models import TimeEntry, TimeActivity
from wiki.models import WikiPage
from core.permissions import get_user_project_permissions

from .serializers import (
    ProjectSerializer,
    IssueSerializer, JournalSerializer, JournalCreateSerializer,
    IssueStatusSerializer, IssuePrioritySerializer, TrackerSerializer,
    VersionSerializer,
    TimeEntrySerializer, TimeActivitySerializer,
    WikiPageSerializer,
)
from .permissions import ProjectReadPermission, HasProjectPerm

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TokenView(ObtainAuthToken):
    """
    POST /api/v1/auth/token/
    Body : { "username": "…", "password": "…" }
    Réponse : { "token": "…", "user_id": …, "username": "…" }
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username,
        })


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/v1/projects/          — liste des projets visibles
    GET /api/v1/projects/{pk}/     — détail
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "is_public"]
    search_fields = ["name", "identifier", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        member_ids = Membership.objects.filter(user=user).values_list("project_id", flat=True)
        return Project.objects.filter(
            models_Q(id__in=member_ids) | models_Q(is_public=True)
        ).distinct()

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        """GET /api/v1/projects/{pk}/members/"""
        project = self.get_object()
        memberships = (
            Membership.objects.filter(project=project)
            .select_related("user")
            .prefetch_related("roles")
        )
        data = [
            {
                "user": {
                    "id": m.user_id,
                    "username": m.user.username,
                    "full_name": m.user.get_full_name() or m.user.username,
                },
                "roles": [r.name for r in m.roles.all()],
            }
            for m in memberships
        ]
        return Response(data)


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

class IssueViewSet(viewsets.ModelViewSet):
    """
    GET    /api/v1/issues/         — liste (filtrable par ?project=, ?status=, etc.)
    POST   /api/v1/issues/         — créer un ticket
    GET    /api/v1/issues/{pk}/    — détail
    PATCH  /api/v1/issues/{pk}/    — mise à jour partielle
    DELETE /api/v1/issues/{pk}/    — suppression (superuser ou manage_project)

    Actions supplémentaires :
    GET/POST /api/v1/issues/{pk}/journals/  — historique + ajout commentaire
    """
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated, ProjectReadPermission, HasProjectPerm]
    read_perms = ["view_issues"]
    write_perms = ["add_issues", "edit_issues"]
    filterset_fields = ["project", "tracker", "status", "priority", "assigned_to"]
    search_fields = ["subject", "description"]
    ordering_fields = ["created_at", "updated_at", "priority__position"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Issue.objects.visible_to(self.request.user)
            .select_related(
                "project", "tracker", "status", "priority",
                "author", "assigned_to", "fixed_version",
            )
        )

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        issue = self.get_object()
        perms = get_user_project_permissions(request.user, issue.project)
        if not request.user.is_superuser and "delete_issues" not in perms:
            return Response(
                {"detail": "Permission insuffisante."},
                status=status.HTTP_403_FORBIDDEN,
            )
        issue.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="journals")
    def journals(self, request, pk=None):
        """
        GET  → liste les entrées de journal du ticket
        POST → ajoute un commentaire (notes)
        """
        issue = self.get_object()

        if request.method == "GET":
            qs = Journal.objects.filter(issue=issue).prefetch_related("details", "user")
            serializer = JournalSerializer(qs, many=True)
            return Response(serializer.data)

        # POST : ajouter un commentaire
        perms = get_user_project_permissions(request.user, issue.project)
        if "add_issues" not in perms and "edit_issues" not in perms:
            return Response(
                {"detail": "Permission insuffisante."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = JournalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from notifications.emails import notify_issue_commented
        journal = Journal.objects.create(
            issue=issue,
            user=request.user,
            notes=serializer.validated_data["notes"],
        )
        notify_issue_commented(issue, journal, actor=request.user)
        return Response(JournalSerializer(journal).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Reference data (read-only)
# ---------------------------------------------------------------------------

class TrackerViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = TrackerSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tracker.objects.all()


class IssueStatusViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = IssueStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = IssueStatus.objects.all()


class IssuePriorityViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = IssuePrioritySerializer
    permission_classes = [IsAuthenticated]
    queryset = IssuePriority.objects.all()


class TimeActivityViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = TimeActivitySerializer
    permission_classes = [IsAuthenticated]
    queryset = TimeActivity.objects.all()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

class VersionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/v1/versions/          — toutes versions des projets visibles
    GET /api/v1/versions/{pk}/     — détail (+ compteurs tickets)
    Filtre : ?project=<pk>
    """
    serializer_class = VersionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["project", "status", "sharing"]
    ordering_fields = ["due_date", "name"]
    ordering = ["due_date"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Version.objects.select_related("project").all()
        member_ids = Membership.objects.filter(user=user).values_list("project_id", flat=True)
        public_ids = Project.objects.filter(is_public=True).values_list("id", flat=True)
        visible = set(member_ids) | set(public_ids)
        return Version.objects.filter(project_id__in=visible).select_related("project")


# ---------------------------------------------------------------------------
# Time entries
# ---------------------------------------------------------------------------

class TimeEntryViewSet(viewsets.ModelViewSet):
    """
    GET    /api/v1/time-entries/         — liste (filtrable par ?project=, ?issue=)
    POST   /api/v1/time-entries/         — créer
    GET    /api/v1/time-entries/{pk}/    — détail
    PATCH  /api/v1/time-entries/{pk}/    — modifier
    DELETE /api/v1/time-entries/{pk}/    — supprimer
    """
    serializer_class = TimeEntrySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["project", "issue", "activity", "user"]
    ordering_fields = ["spent_on", "hours", "created_at"]
    ordering = ["-spent_on"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            TimeEntry.objects.visible_to(self.request.user)
            .select_related("user", "project", "issue", "activity")
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not obj.can_be_edited_by(request.user):
                self.permission_denied(
                    request, message="Vous ne pouvez modifier que vos propres saisies."
                )


# ---------------------------------------------------------------------------
# Wiki
# ---------------------------------------------------------------------------

class WikiPageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/v1/wiki/          — liste des pages wiki des projets visibles
    GET /api/v1/wiki/{pk}/     — détail avec contenu rendu
    Filtres : ?project=<pk>  ?slug=<slug>
    """
    serializer_class = WikiPageSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["project", "slug"]
    search_fields = ["title", "slug"]
    ordering_fields = ["title", "updated_at"]
    ordering = ["title"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return WikiPage.objects.select_related("project").prefetch_related(
                "revisions"
            ).all()
        member_ids = Membership.objects.filter(user=user).values_list("project_id", flat=True)
        public_ids = Project.objects.filter(is_public=True).values_list("id", flat=True)
        visible = set(member_ids) | set(public_ids)
        return (
            WikiPage.objects.filter(project_id__in=visible)
            .select_related("project")
            .prefetch_related("revisions")
        )


