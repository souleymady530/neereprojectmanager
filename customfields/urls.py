from django.urls import path
from . import views

app_name = "customfields"

urlpatterns = [
    path("", views.CustomFieldListView.as_view(), name="list"),
    path("new/", views.CustomFieldCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.CustomFieldUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.CustomFieldDeleteView.as_view(), name="delete"),
]
