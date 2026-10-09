from django.contrib import admin
from .models import (
    Tracker, IssueStatus, IssuePriority, Issue,
    WorkflowTransition, Journal, JournalDetail, IssueRelation,
)


@admin.register(Tracker)
class TrackerAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "default_status"]
    ordering = ["position"]


@admin.register(IssueStatus)
class IssueStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "is_closed", "position"]
    ordering = ["position"]


@admin.register(IssuePriority)
class IssuePriorityAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "is_default", "color"]
    ordering = ["position"]


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = ["tracker", "role", "old_status", "new_status"]
    list_filter = ["tracker", "role"]


class JournalDetailInline(admin.TabularInline):
    model = JournalDetail
    extra = 0
    readonly_fields = ["field", "old_value", "new_value"]


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ["issue", "user", "created_at"]
    inlines = [JournalDetailInline]


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["pk", "subject", "project", "tracker", "status", "priority", "assigned_to", "created_at"]
    list_filter = ["project", "tracker", "status", "priority"]
    search_fields = ["subject", "description"]
    raw_id_fields = ["parent", "assigned_to", "author"]
