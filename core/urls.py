from django.urls import path
from django.views.generic import RedirectView
from .search_views import SearchView

urlpatterns = [
    path("", RedirectView.as_view(url="/my/page/", permanent=False), name="home"),
    path("search/", SearchView.as_view(), name="search"),
]
