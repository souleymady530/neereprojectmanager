from django.contrib import admin
from .models import WikiPage, WikiPageRevision


class WikiPageRevisionInline(admin.TabularInline):
    model = WikiPageRevision
    extra = 0
    readonly_fields = ["version", "author", "created_at", "comment"]
    fields = ["version", "author", "comment", "created_at"]
    ordering = ["-version"]


@admin.register(WikiPage)
class WikiPageAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "project", "version", "updated_at"]
    list_filter = ["project"]
    search_fields = ["title", "slug"]
    inlines = [WikiPageRevisionInline]
    readonly_fields = ["slug", "created_at", "updated_at"]


@admin.register(WikiPageRevision)
class WikiPageRevisionAdmin(admin.ModelAdmin):
    list_display = ["page", "version", "author", "comment", "created_at"]
    list_filter = ["page__project"]
    readonly_fields = ["version", "created_at"]
