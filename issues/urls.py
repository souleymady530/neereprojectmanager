from django.urls import path
from . import views

app_name = "issues"

urlpatterns = [
    # Kanban (vue par défaut)
    path("", views.KanbanView.as_view(), name="kanban"),
    # Liste tabulaire
    path("list/", views.IssueListView.as_view(), name="list"),
    path("<int:pk>/", views.IssueDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.IssueUpdateView.as_view(), name="edit"),
    # Actions HTMX / JS
    path("<int:pk>/notes/", views.IssueAddNoteView.as_view(), name="add_note"),
    path("<int:pk>/status/", views.IssueStatusUpdateView.as_view(), name="update_status"),
    path("<int:pk>/done-ratio/", views.IssueDoneRatioUpdateView.as_view(), name="update_done_ratio"),
    path("<int:pk>/watch/", views.IssueWatchToggleView.as_view(), name="watch_toggle"),
    path("<int:pk>/move/", views.KanbanMoveView.as_view(), name="kanban_move"),
]
