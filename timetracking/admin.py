from django.contrib import admin
from .models import TimeActivity, TimeEntry


@admin.register(TimeActivity)
class TimeActivityAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "is_default"]
    ordering = ["position"]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "issue", "activity", "hours", "spent_on"]
    list_filter = ["project", "activity", "spent_on"]
    search_fields = ["comment", "user__username"]
    raw_id_fields = ["issue"]
    date_hierarchy = "spent_on"
