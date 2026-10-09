from django.urls import path
from . import views

# Inclus sous projects/<identifier>/
# app_name géré depuis projects/urls.py (namespace "projects")

urlpatterns = [
    path("versions/new/", views.VersionCreateView.as_view(), name="version_create"),
    path("versions/<int:pk>/edit/", views.VersionUpdateView.as_view(), name="version_edit"),
    path("versions/<int:pk>/delete/", views.VersionDeleteView.as_view(), name="version_delete"),
    path("roadmap/", views.RoadmapView.as_view(), name="roadmap"),
]
