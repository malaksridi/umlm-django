from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.views import (
    ProjectViewSet, ModuleViewSet, ProjectModuleViewSet,
    MiseAJourViewSet, AlertViewSet, DashboardView, dashboard_page,
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
]
