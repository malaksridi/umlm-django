from django.contrib import admin
from django.urls import path, include
from core.views import dashboard_view, select_user_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", select_user_view, name="select_user"),  # anonymous landing page
    path("dashboard/", dashboard_view, name="dashboard"),
    path("api/", include("core.urls")),
]
