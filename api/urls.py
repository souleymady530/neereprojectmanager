from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("projects", views.ProjectViewSet, basename="project")
router.register("issues", views.IssueViewSet, basename="issue")
router.register("versions", views.VersionViewSet, basename="version")
router.register("time-entries", views.TimeEntryViewSet, basename="timeentry")
router.register("wiki", views.WikiPageViewSet, basename="wiki")
router.register("trackers", views.TrackerViewSet, basename="tracker")
router.register("statuses", views.IssueStatusViewSet, basename="status")
router.register("priorities", views.IssuePriorityViewSet, basename="priority")
router.register("activities", views.TimeActivityViewSet, basename="activity")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/", views.TokenView.as_view(), name="api-token"),
]
