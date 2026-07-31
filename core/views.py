import json
import traceback
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.response import Response

from .ai_service import generate_chat_response
from .auth import get_current_user, GLOBAL_VIEW_ROLES
from .models import User, Project, Module, ProjectModule, MiseAJour, Alert
from core.serializers import (
    ProjectSerializer, ModuleSerializer, ProjectModuleSerializer,
    MiseAJourSerializer, AlertSerializer,
)

PROBLEMATIC_STATUSES = ["behind", "non_integre", "diverged"]


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_historique_data():
    """
    Historique mensuel (cahier des charges 4.6 : "Générer des graphiques
    mensuels") du nombre de problèmes détectés (retard/absent/diverged).
    """
    rows = (
        MiseAJour.objects
        .filter(status__in=PROBLEMATIC_STATUSES)
        .annotate(month=TruncMonth("scanned_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    labels = [row["month"].strftime("%m/%Y") for row in rows]
    values = [row["total"] for row in rows]
    return labels, values


def get_kpis(project_modules_qs):
    """
    Indicateurs (cahier des charges section 5). Certains KPIs de la
    section 5 (temps moyen avant intégration, moyenne de commits de
    retard) nécessitent des données non encore trackées (timestamps de
    scan par module, vrai diff de commits) et sont volontairement omis
    ici plutôt que d'afficher un chiffre inventé — à ajouter en V1.1.
    """
    total = project_modules_qs.count()
    up_to_date = project_modules_qs.filter(status="up_to_date").count()
    pct_up_to_date = round((up_to_date / total) * 100, 1) if total else 0

    critiques_en_retard = project_modules_qs.filter(
        status="behind", module__criticality="critique"
    ).count()

    top_modules = (
        Module.objects
        .annotate(nb_installations=Count("project_modules"))
        .order_by("-nb_installations")[:5]
    )

    top_projets = []
    for project in Project.objects.prefetch_related("project_modules"):
        pms = project.project_modules.all()
        pm_total = pms.count()
        if pm_total == 0:
            continue
        pm_up_to_date = sum(1 for pm in pms if pm.status == "up_to_date")
        top_projets.append({
            "project": project,
            "pct_up_to_date": round((pm_up_to_date / pm_total) * 100, 1),
        })
    top_projets = sorted(top_projets, key=lambda x: x["pct_up_to_date"], reverse=True)[:5]

    return {
        "pct_up_to_date": pct_up_to_date,
        "critiques_en_retard": critiques_en_retard,
        "top_modules": top_modules,
        "top_projets": top_projets,
    }


# ==========================================
# STANDARD DJANGO PAGE VIEWS
# ==========================================

def select_user_view(request):
    if request.method == "POST":
        request.session["user_id"] = request.POST.get("user_id")
        request.session.set_expiry(60 * 60 * 24 * 90)
        return redirect("dashboard")
    users = User.objects.select_related("role").all()
    return render(request, "core/select_user.html", {"users": users})


def dashboard_page(request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect("select_user")

    role_name = getattr(current_user.role, "name", "").lower()

    # Développeur : restreint aux projets assignés à son rôle (section 3 :
    # "Consultation des projets assignés"). Les autres rôles voient tout.
    if role_name in GLOBAL_VIEW_ROLES:
        projects = Project.objects.prefetch_related("project_modules__module").all()
    else:
        projects = Project.objects.filter(roles=current_user.role).prefetch_related(
            "project_modules__module"
        ).distinct()

    project_ids = projects.values_list("id", flat=True)
    modules = Module.objects.filter(
        project_modules__project_id__in=project_ids
    ).distinct().prefetch_related("project_modules__project")

    project_modules_qs = ProjectModule.objects.filter(project_id__in=project_ids)

    recent_alerts = (
        Alert.objects
        .filter(mise_a_jour__project_module__project_id__in=project_ids)
        .select_related("mise_a_jour__project_module__project", "mise_a_jour__project_module__module")
        .order_by("-sent_at")[:10]
    )
    chart_labels, chart_values = get_historique_data()
    kpis = get_kpis(project_modules_qs)

    context = {
        "projects": projects,
        "modules": modules,
        "recent_alerts": recent_alerts,
        "total_projects": projects.count(),
        "total_project_modules": project_modules_qs.count(),
        "en_retard": project_modules_qs.filter(status="behind").count(),
        "absents": project_modules_qs.filter(status="non_integre").count(),
        "last_updated": timezone.now(),
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
        # KPIs (section 5)
        "kpi_pct_up_to_date": kpis["pct_up_to_date"],
        "kpi_critiques_en_retard": kpis["critiques_en_retard"],
        "kpi_top_modules": kpis["top_modules"],
        "kpi_top_projets": kpis["top_projets"],
    }
    return render(request, "core/dashboard.html", context)


# Alias so both dashboard_page and dashboard_view work in urls.py
dashboard_view = dashboard_page


def projects_list_view(request):
    projects = Project.objects.prefetch_related('project_modules__module').all()
    return render(request, 'projects.html', {'projects': projects})


def logout_view(request):
    request.session.flush()
    return redirect("/")


# ==========================================
# AI CHATBOT ENDPOINT
# ==========================================

@csrf_exempt
def chat_ai_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")
            if not user_message.strip():
                return JsonResponse({"error": "Message cannot be empty."}, status=400)
            
            reply = generate_chat_response(user_message)
            return JsonResponse({"reply": reply})
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"error": f"Backend Error: {str(e)}"}, status=500)
    
    return JsonResponse({"error": "Method not allowed."}, status=405)


# ==========================================
# REST FRAMEWORK VIEWSETS (API)
# ==========================================

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
