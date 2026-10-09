from django.contrib import admin
from .models import Project, Role, Membership


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "position"]
    ordering = ["position"]


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1
    filter_horizontal = ["roles"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "identifier", "parent", "is_public", "status", "created_at"]
    list_filter = ["status", "is_public"]
    search_fields = ["name", "identifier"]
    prepopulated_fields = {"identifier": ("name",)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "created_at"]
    list_filter = ["project"]
    filter_horizontal = ["roles"]
