from django.urls import path
from . import views
from issues.views import IssueListView, IssueCreateView, KanbanView, IssueImportView
from versions.views import RoadmapView, VersionCreateView, VersionUpdateView, VersionDeleteView
from timetracking.views import TimeEntryListView, TimeEntryCreateView, TimeReportView
from wiki import views as wiki_views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="list"),
    path("new/", views.ProjectCreateView.as_view(), name="create"),
    path("<slug:identifier>/", views.ProjectOverviewView.as_view(), name="overview"),
    path("<slug:identifier>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
    path("<slug:identifier>/delete/", views.ProjectDeleteView.as_view(), name="delete"),
    path("<slug:identifier>/settings/", views.ProjectSettingsView.as_view(), name="settings"),
    path("<slug:identifier>/members/add/", views.MemberAddView.as_view(), name="member_add"),
    path("<slug:identifier>/members/<int:pk>/remove/", views.MemberRemoveView.as_view(), name="member_remove"),
    path("<slug:identifier>/invitations/new/", views.InvitationCreateView.as_view(), name="invitation_create"),
    path("<slug:identifier>/invitations/<int:pk>/revoke/", views.InvitationRevokeView.as_view(), name="invitation_revoke"),
    # Tickets scoped au projet (kanban = défaut, list = vue tabulaire)
    path("<slug:identifier>/issues/", KanbanView.as_view(), name="issue_list"),
    path("<slug:identifier>/issues/list/", IssueListView.as_view(), name="issue_list_table"),
    path("<slug:identifier>/issues/new/", IssueCreateView.as_view(), name="issue_create"),
    path("<slug:identifier>/issues/import/", IssueImportView.as_view(), name="issue_import"),
    # Temps
    path("<slug:identifier>/time_entries/", TimeEntryListView.as_view(), name="time_entries"),
    path("<slug:identifier>/time_entries/new/", TimeEntryCreateView.as_view(), name="time_entry_create"),
    path("<slug:identifier>/time_entries/report/", TimeReportView.as_view(), name="time_report"),
    # Wiki
    path("<slug:identifier>/wiki/", wiki_views.WikiHomeView.as_view(), name="wiki_home"),
    path("<slug:identifier>/wiki/index/", wiki_views.WikiPageListView.as_view(), name="wiki_list"),
    path("<slug:identifier>/wiki/<slug:slug>/", wiki_views.WikiPageView.as_view(), name="wiki_page"),
    path("<slug:identifier>/wiki/<slug:slug>/edit/", wiki_views.WikiPageEditView.as_view(), name="wiki_edit"),
    path("<slug:identifier>/wiki/<slug:slug>/history/", wiki_views.WikiPageHistoryView.as_view(), name="wiki_history"),
    path("<slug:identifier>/wiki/<slug:slug>/diff/", wiki_views.WikiPageDiffView.as_view(), name="wiki_diff"),
    path("<slug:identifier>/wiki/<slug:slug>/revision/<int:version>/", wiki_views.WikiPageRevisionView.as_view(), name="wiki_revision"),
    path("<slug:identifier>/wiki/<slug:slug>/revision/<int:version>/rollback/", wiki_views.WikiPageRollbackView.as_view(), name="wiki_rollback"),
    path("<slug:identifier>/wiki/<slug:slug>/delete/", wiki_views.WikiPageDeleteView.as_view(), name="wiki_delete"),
    # Gantt
    path("<slug:identifier>/gantt/", views.GanttView.as_view(), name="gantt"),
    # Versions + roadmap
    path("<slug:identifier>/roadmap/", RoadmapView.as_view(), name="roadmap"),
    path("<slug:identifier>/versions/new/", VersionCreateView.as_view(), name="version_create"),
    path("<slug:identifier>/versions/<int:pk>/edit/", VersionUpdateView.as_view(), name="version_edit"),
    path("<slug:identifier>/versions/<int:pk>/delete/", VersionDeleteView.as_view(), name="version_delete"),
]
