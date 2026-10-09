from django.contrib import admin
from .models import Version


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "status", "effective_date"]
    list_filter = ["project", "status"]
