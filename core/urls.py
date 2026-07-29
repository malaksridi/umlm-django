# Destination: core/urls.py  (replace the whole file)
from . import views_manage
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.views import (
    ProjectViewSet, ModuleViewSet, ProjectModuleViewSet,
    MiseAJourViewSet, AlertViewSet, DashboardView,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet)
router.register(r"modules", ModuleViewSet)
router.register(r"project-modules", ProjectModuleViewSet)
router.register(r"mises-a-jour", MiseAJourViewSet)
router.register(r"alerts", AlertViewSet)
router.register(r"dashboard-api", DashboardView, basename="dashboard-api")

urlpatterns = [
    path("", include(router.urls)),

    path("manage/projects/", views_manage.project_list, name="project_list"),
    path("manage/projects/add/", views_manage.project_add, name="project_add"),
    path("manage/projects/<int:pk>/edit/", views_manage.project_edit, name="project_edit"),
    path("manage/projects/<int:pk>/delete/", views_manage.project_delete, name="project_delete"),

    path("manage/modules/", views_manage.module_list, name="module_list"),
    path("manage/modules/add/", views_manage.module_add, name="module_add"),
    path("manage/modules/<int:pk>/edit/", views_manage.module_edit, name="module_edit"),
    path("manage/modules/<int:pk>/delete/", views_manage.module_delete, name="module_delete"),

    path("manage/roles/", views_manage.role_list, name="role_list"),
    path("manage/roles/add/", views_manage.role_add, name="role_add"),
    path("manage/roles/<int:pk>/edit/", views_manage.role_edit, name="role_edit"),
    path("manage/roles/<int:pk>/delete/", views_manage.role_delete, name="role_delete"),

    path("manage/users/", views_manage.user_list, name="user_list"),
    path("manage/users/add/", views_manage.user_add, name="user_add"),
    path("manage/users/<int:pk>/edit/", views_manage.user_edit, name="user_edit"),
    path("manage/users/<int:pk>/delete/", views_manage.user_delete, name="user_delete"),
]
