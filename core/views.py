# Destination: core/views.py  (replace the whole file)
import json
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response

from .auth import get_current_user
from .models import User
from core.models import Project, Module, ProjectModule, MiseAJour, Alert
from core.serializers import (
    ProjectSerializer, ModuleSerializer, ProjectModuleSerializer,
    MiseAJourSerializer, AlertSerializer,
)

PROBLEMATIC_STATUSES = ["behind", "non_integre", "diverged"]


def get_historique_data():
    """
    Regroupe les MiseAJour par jour et compte combien de modules étaient
    en problème (en retard, absent, divergé) ce jour-là.
    Alimente le graphique d'évolution (section 4.6).
    """
    rows = (
        MiseAJour.objects
        .filter(status__in=PROBLEMATIC_STATUSES)
        .annotate(day=TruncDate("scanned_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    labels = [row["day"].strftime("%d/%m") for row in rows]
    values = [row["total"] for row in rows]
    return labels, values


def select_user_view(request):
    if request.method == "POST":
        request.session["user_id"] = request.POST.get("user_id")
        request.session.set_expiry(60 * 60 * 24 * 90)  # reste "connecté" 90 jours
        return redirect("dashboard")
    users = User.objects.select_related("role").all()
    return render(request, "core/select_user.html", {"users": users})


def dashboard_page(request):
    """
    Vue "page web" (pas API) — affiche le dashboard visuel.
    Section 4.4 du cahier des charges.
    """
    if not get_current_user(request):
        return redirect("/")

    projects = Project.objects.prefetch_related("project_modules__module").all()
    modules = Module.objects.prefetch_related("project_modules__project").all()
    recent_alerts = (
        Alert.objects
        .select_related("mise_a_jour__project_module__project", "mise_a_jour__project_module__module")
        .order_by("-sent_at")[:10]
    )
    chart_labels, chart_values = get_historique_data()

    context = {
        "projects": projects,
        "modules": modules,
        "recent_alerts": recent_alerts,
        "total_projects": projects.count(),
        "total_project_modules": ProjectModule.objects.count(),
        "en_retard": ProjectModule.objects.filter(status="behind").count(),
        "absents": ProjectModule.objects.filter(status="non_integre").count(),
        "last_updated": timezone.now(),
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
    }
    return render(request, "core/dashboard.html", context)


def logout_view(request):
    request.session.flush()
    return redirect("/")


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer


class ProjectModuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProjectModule.objects.select_related("project", "module").all()
    serializer_class = ProjectModuleSerializer


class MiseAJourViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MiseAJour.objects.all().order_by("-scanned_at")
    serializer_class = MiseAJourSerializer


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alert.objects.all().order_by("-sent_at")
    serializer_class = AlertSerializer


class DashboardView(viewsets.ViewSet):
    """
    Équivalent API (JSON) de la section 4.4 "Dashboard" du cahier des charges :
    vue globale (nb projets, modules, en retard, absents).
    """

    def list(self, request):
        total_projects = Project.objects.count()
        en_retard = ProjectModule.objects.filter(status="behind").count()
        absents = ProjectModule.objects.filter(status="non_integre").count()

        return Response({
            "projets": total_projects,
            "modules_installes": ProjectModule.objects.count(),
            "en_retard": en_retard,
            "absents": absents,
        })
