from django.urls import path
from . import views

# Inclus dans projects/urls.py avec le préfixe <slug:identifier>/wiki/
urlpatterns = [
    path("", views.WikiHomeView.as_view(), name="wiki_home"),
    path("index/", views.WikiPageListView.as_view(), name="wiki_list"),
    path("<slug:slug>/", views.WikiPageView.as_view(), name="wiki_page"),
    path("<slug:slug>/edit/", views.WikiPageEditView.as_view(), name="wiki_edit"),
    path("<slug:slug>/history/", views.WikiPageHistoryView.as_view(), name="wiki_history"),
    path("<slug:slug>/diff/", views.WikiPageDiffView.as_view(), name="wiki_diff"),
    path("<slug:slug>/revision/<int:version>/", views.WikiPageRevisionView.as_view(), name="wiki_revision"),
    path("<slug:slug>/revision/<int:version>/rollback/", views.WikiPageRollbackView.as_view(), name="wiki_rollback"),
    path("<slug:slug>/delete/", views.WikiPageDeleteView.as_view(), name="wiki_delete"),
]
