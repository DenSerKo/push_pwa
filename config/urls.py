from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from django.http import FileResponse, HttpResponse
from django.conf import settings
from pathlib import Path

def service_worker(request):
    response = FileResponse(
        open(Path(settings.BASE_DIR) / "static" / "service-worker.js", "rb"),
        content_type="application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response

def manifest(request):
    response = FileResponse(
        open(Path(settings.BASE_DIR) / "static" / "manifest.json", "rb"),
        content_type="application/manifest+json",
    )
    response["Cache-Control"] = "no-cache"
    return response

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("service-worker.js", service_worker, name="service_worker"),
    path("manifest.json", manifest, name="manifest"),
    path("", include("pushdemo.urls")),
]
