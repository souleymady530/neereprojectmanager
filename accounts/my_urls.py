from django.urls import path
from . import views
from notifications.views import NotificationPreferenceView

app_name = "my"

urlpatterns = [
    path("page/", views.MyPageView.as_view(), name="page"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("notifications/", NotificationPreferenceView.as_view(), name="notifications"),
]
