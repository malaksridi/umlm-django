import json
import traceback
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.response import Response

from .ai_service import generate_chat_response
from .auth import get_current_user
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
    if not get_current_user(request):
        return redirect("select_user")

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
