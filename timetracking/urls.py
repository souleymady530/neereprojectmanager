from django.urls import path
from . import views

app_name = "timetracking"

urlpatterns = [
    # Actions sur une saisie (sans contexte projet)
    path("<int:pk>/edit/", views.TimeEntryUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.TimeEntryDeleteView.as_view(), name="delete"),
]
