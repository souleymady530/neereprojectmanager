from django.contrib import admin
from .models import NotificationPreference


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user", "notify_assigned", "notify_issue_updated",
        "notify_issue_commented", "notify_wiki_edited",
    ]
    list_filter = ["notify_assigned", "notify_wiki_edited"]
    search_fields = ["user__username", "user__email"]
