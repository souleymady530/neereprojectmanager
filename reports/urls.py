from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="list"),
    path("new/", views.ReportCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ReportDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ReportUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ReportDeleteView.as_view(), name="delete"),
    path("<int:pk>/export/", views.ReportExportCSVView.as_view(), name="export_csv"),
]
