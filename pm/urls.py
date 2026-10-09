from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("projects/", include("projects.urls")),
    path("issues/", include("issues.urls")),
    path("my/", include("accounts.my_urls")),
    path("time_entries/", include("timetracking.urls")),
    path("api/v1/", include("api.urls")),
    path("custom-fields/", include("customfields.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
