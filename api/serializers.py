from rest_framework import serializers

from projects.models import Project, Membership, Role
from issues.models import (
    Issue, IssueStatus, IssuePriority, Tracker,
    Journal, JournalDetail,
)
from versions.models import Version
from timetracking.models import TimeEntry, TimeActivity
from wiki.models import WikiPage, WikiPageRevision


# ---------------------------------------------------------------------------
# Shared tiny serializers
# ---------------------------------------------------------------------------

class UserMinimalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ---------------------------------------------------------------------------
# Reference / lookup resources
# ---------------------------------------------------------------------------

class TrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracker
        fields = ["id", "name", "position"]


class IssueStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueStatus
        fields = ["id", "name", "is_closed", "position"]


class IssuePrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = IssuePriority
        fields = ["id", "name", "position", "is_default", "color"]


class TimeActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeActivity
        fields = ["id", "name", "position", "is_default"]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id", "name", "identifier", "description",
            "is_public", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

class JournalDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalDetail
        fields = ["field", "old_value", "new_value"]


class JournalSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    details = JournalDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Journal
        fields = ["id", "user", "notes", "details", "created_at"]
        read_only_fields = ["id", "user", "details", "created_at"]


class JournalCreateSerializer(serializers.Serializer):
    notes = serializers.CharField(allow_blank=False)


class IssueSerializer(serializers.ModelSerializer):
    tracker = TrackerSerializer(read_only=True)
    tracker_id = serializers.PrimaryKeyRelatedField(
        queryset=Tracker.objects.all(), source="tracker", write_only=True
    )
    status = IssueStatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=IssueStatus.objects.all(), source="status", write_only=True, required=False
    )
    priority = IssuePrioritySerializer(read_only=True)
    priority_id = serializers.PrimaryKeyRelatedField(
        queryset=IssuePriority.objects.all(), source="priority", write_only=True
    )
    author = UserMinimalSerializer(read_only=True)
    assigned_to = UserMinimalSerializer(read_only=True)
    assigned_to_id = serializers.IntegerField(
        allow_null=True, required=False, write_only=True
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source="project", write_only=True
    )
    version = serializers.SerializerMethodField()
    version_id = serializers.PrimaryKeyRelatedField(
        queryset=Version.objects.all(), source="fixed_version",
        write_only=True, allow_null=True, required=False
    )
    journals_count = serializers.SerializerMethodField()
    custom_fields = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "project", "project_id",
            "tracker", "tracker_id",
            "subject", "description",
            "status", "status_id",
            "priority", "priority_id",
            "author",
            "assigned_to", "assigned_to_id",
            "version", "version_id",
            "start_date", "due_date",
            "estimated_hours", "done_ratio",
            "custom_fields",
            "journals_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "author", "created_at", "updated_at",
            "journals_count", "custom_fields",
        ]

    def get_version(self, obj):
        if obj.fixed_version_id:
            return {"id": obj.fixed_version_id, "name": str(obj.fixed_version)}
        return None

    def get_journals_count(self, obj):
        if hasattr(obj, "_journals_count"):
            return obj._journals_count
        return obj.journals.count()

    def get_custom_fields(self, obj):
        from customfields.utils import human_value
        values = {cv.field_id: cv.value for cv in obj.custom_values.select_related("field")}
        return [
            {
                "id": cv.field_id,
                "name": cv.field.name,
                "type": cv.field.field_type,
                "value": human_value(cv.field, cv.value),
                "raw_value": cv.value,
            }
            for cv in obj.custom_values.select_related("field")
            if values.get(cv.field_id, "") != ""
        ]

    def validate_assigned_to_id(self, value):
        if value is None:
            return None
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Utilisateur introuvable.")

    def create(self, validated_data):
        assigned = validated_data.pop("assigned_to_id", None)
        issue = Issue(**validated_data)
        issue.author = self.context["request"].user
        if assigned:
            issue.assigned_to = assigned
        if not issue.status_id and issue.tracker.default_status:
            issue.status = issue.tracker.default_status
        issue.save()
        return issue

    def update(self, instance, validated_data):
        from issues.services import update_issue
        assigned = validated_data.pop("assigned_to_id", _MISSING)
        data = dict(validated_data)
        if assigned is not _MISSING:
            data["assigned_to"] = assigned
        update_issue(instance, self.context["request"].user, data)
        instance.refresh_from_db()
        return instance


_MISSING = object()


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

class VersionSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    progress = serializers.IntegerField(read_only=True)
    open_issues_count = serializers.SerializerMethodField()
    closed_issues_count = serializers.SerializerMethodField()

    class Meta:
        model = Version
        fields = [
            "id", "project", "name", "description",
            "due_date", "status", "sharing",
            "progress", "open_issues_count", "closed_issues_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "project", "progress", "created_at", "updated_at"]

    def get_open_issues_count(self, obj):
        return obj.issues.filter(status__is_closed=False).count()

    def get_closed_issues_count(self, obj):
        return obj.issues.filter(status__is_closed=True).count()


# ---------------------------------------------------------------------------
# Time entries
# ---------------------------------------------------------------------------

class TimeEntrySerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source="project", write_only=True
    )
    issue_id = serializers.PrimaryKeyRelatedField(
        queryset=Issue.objects.all(), source="issue",
        write_only=True, allow_null=True, required=False
    )
    issue_subject = serializers.SerializerMethodField()
    activity = TimeActivitySerializer(read_only=True)
    activity_id = serializers.PrimaryKeyRelatedField(
        queryset=TimeActivity.objects.all(), source="activity", write_only=True
    )

    class Meta:
        model = TimeEntry
        fields = [
            "id", "user", "project", "project_id",
            "issue_id", "issue_subject",
            "activity", "activity_id",
            "hours", "spent_on", "comment",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_issue_subject(self, obj):
        if obj.issue_id:
            return str(obj.issue)
        return None

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Wiki
# ---------------------------------------------------------------------------

class WikiPageRevisionSerializer(serializers.ModelSerializer):
    author = UserMinimalSerializer(read_only=True)

    class Meta:
        model = WikiPageRevision
        fields = ["version", "author", "comment", "created_at"]


class WikiPageSerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    current_revision = WikiPageRevisionSerializer(read_only=True)
    rendered_content = serializers.SerializerMethodField()

    class Meta:
        model = WikiPage
        fields = [
            "id", "project", "title", "slug",
            "current_revision", "rendered_content",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_rendered_content(self, obj):
        from wiki.utils import render_markdown
        if obj.content:
            html, _ = render_markdown(obj.content, obj.project.identifier)
            return html
        return ""
