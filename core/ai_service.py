import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from core.models import Project, Module, ProjectModule, Alert, User, Role

load_dotenv()
logger = logging.getLogger(__name__)

# Safety cap per list so we don't blow up the prompt on a huge dataset.
MAX_ITEMS = 200


def _build_context() -> str:
    """Builds a detailed, human-readable snapshot of the whole system for the AI."""

    # ---------- Rôles ----------
    roles = list(Role.objects.all()[:MAX_ITEMS])
    roles_lines = []
    for r in roles:
        droits = []
        if r.droit_gestion_complete: droits.append("Gestion complète")
        if r.droit_consultation: droits.append("Consultation")
        if r.droit_alertes: droits.append("Alertes")
        if r.droit_consultation_projets_assignes: droits.append("Consultation des projets assignés")
        if r.droit_vue_globale_statistiques: droits.append("Vue globale et statistiques")
        droits_str = ", ".join(droits) if droits else "aucun droit défini"
        roles_lines.append(f"  - {r.name} : {droits_str}")
    roles_block = "\n".join(roles_lines) if roles_lines else "  (aucun rôle défini)"

    # ---------- Utilisateurs ----------
    users = list(User.objects.select_related("role").all()[:MAX_ITEMS])
    users_lines = [f"  - {u.name} ({u.email}) — rôle : {u.role.name}" for u in users]
    users_block = "\n".join(users_lines) if users_lines else "  (aucun utilisateur défini)"

    # ---------- Projets ----------
    projects = list(Project.objects.all()[:MAX_ITEMS])
    projects_lines = [
        f"  - {p.name} (dépôt GitHub : {p.github_url}, branche de référence : {p.reference_branch})"
        for p in projects
    ]
    projects_block = "\n".join(projects_lines) if projects_lines else "  (aucun projet défini)"

    # ---------- Modules ----------
    modules = list(Module.objects.all()[:MAX_ITEMS])
    modules_lines = [
        f"  - {m.name} (dépôt : {m.github_url}, branche : {m.reference_branch}, "
        f"criticité : {m.criticality}, fork personnalisé : {'oui' if m.is_custom_fork else 'non'})"
        for m in modules
    ]
    modules_block = "\n".join(modules_lines) if modules_lines else "  (aucun module défini)"

    # ---------- État des modules par projet ----------
    project_modules = list(
        ProjectModule.objects.select_related("project", "module")[:MAX_ITEMS]
    )
    pm_lines = [
        f"  - {pm.project.name} / {pm.module.name} : {pm.status}"
        for pm in project_modules
    ]
    pm_block = "\n".join(pm_lines) if pm_lines else "  (aucune association projet-module)"

    # ---------- Alertes récentes ----------
    alerts = list(Alert.objects.select_related(
        "mise_a_jour__project_module__project", "mise_a_jour__project_module__module"
    ).order_by("-sent_at")[:50])
    alerts_lines = []
    for a in alerts:
        pm = a.mise_a_jour.project_module
        alerts_lines.append(
            f"  - [{a.sent_at:%d/%m/%Y %H:%M}] {a.type} sur {pm.project.name}/{pm.module.name} "
            f"(canal : {a.channel})"
        )
    alerts_block = "\n".join(alerts_lines) if alerts_lines else "  (aucune alerte envoyée)"

    # ---------- Agrégats ----------
    en_retard_count = ProjectModule.objects.filter(status="behind").count()
    absents_count = ProjectModule.objects.filter(status="non_integre").count()

    return (
        f"=== STATISTIQUES GLOBALES ===\n"
        f"Utilisateurs : {len(users)}\n"
        f"Projets : {len(projects)}\n"
        f"Modules définis : {len(modules)}\n"
        f"Associations projet-module : {ProjectModule.objects.count()}\n"
        f"Modules en retard (behind) : {en_retard_count}\n"
        f"Modules absents (non_integre) : {absents_count}\n"
        f"Rôles : {len(roles)}\n"
        f"Alertes envoyées (total) : {Alert.objects.count()}\n\n"
        f"=== RÔLES ET DROITS ===\n{roles_block}\n\n"
        f"=== UTILISATEURS ===\n{users_block}\n\n"
        f"=== PROJETS ===\n{projects_block}\n\n"
        f"=== MODULES ===\n{modules_block}\n\n"
        f"=== ÉTAT DES MODULES PAR PROJET ===\n{pm_block}\n\n"
        f"=== ALERTES RÉCENTES (50 dernières) ===\n{alerts_block}\n"
    )


def generate_chat_response(user_message: str) -> str:
    # 1. Check API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ GEMINI_API_KEY is missing from .env file."

    client = genai.Client(api_key=api_key)

    # 2. Build a full snapshot of the system for the AI to draw from
    context = _build_context()

    system_instruction = (
        "Tu es l'assistant IA de UMLM (UPS Module Lifecycle Manager), un tableau de bord "
        "de gestion de projets et de modules logiciels.\n\n"
        "Voici l'état complet et actuel du système. Utilise ces données pour répondre à "
        "TOUTE question sur les projets, modules, rôles, utilisateurs, alertes ou leur état — "
        "n'invente rien qui ne soit pas dans ces données, mais ne dis jamais que l'information "
        "'n'est pas disponible' si elle apparaît ci-dessous.\n\n"
        f"{context}\n\n"
        "Réponds de façon utile, précise et concise, dans la même langue que la question "
        "de l'utilisateur. Si une information précise n'existe vraiment pas dans les données "
        "ci-dessus, dis-le clairement plutôt que d'inventer une réponse."
    )

    # 3. Currently active models, tried in order with a couple retries each
    #    to ride out transient "503 UNAVAILABLE / high demand" errors.
    import time

    models_to_try = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite"]
    last_exception = None

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                    )
                )
                if response.text:
                    return response.text
            except APIError as e:
                logger.warning(f"API Error with {model_name} (attempt {attempt + 1}): {e}")
                last_exception = e
                if getattr(e, "code", None) == 503 and attempt == 0:
                    time.sleep(1.5)
                    continue
                break
            except Exception as e:
                logger.warning(f"Unexpected Error with {model_name}: {e}")
                last_exception = e
                break

    return f"AI Error: Unable to complete request. ({last_exception})"
