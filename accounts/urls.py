from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("invite/<uuid:token>/", views.AcceptInvitationView.as_view(), name="accept_invitation"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
