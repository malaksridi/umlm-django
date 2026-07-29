# Destination: core/auth.py  (replace the whole file)
"""
Authentification maison simplifiée : plus de mot de passe, l'utilisateur
est choisi dans une liste (voir core.views.select_user_view). Chaque
utilisateur garde un rôle unique qui détermine ses droits (section 3 du
cahier des charges).
"""
from functools import wraps

from django.shortcuts import redirect
from rest_framework.permissions import BasePermission

from core.models import User

SESSION_KEY = "user_id"

ROLE_ADMIN = "admin"
ROLE_CHEF_DE_PROJET = "chef_de_projet"
ROLE_DEVELOPPEUR = "developpeur"
ROLE_DIRECTION_TECHNIQUE = "direction_technique"

# Rôles qui voient TOUS les projets (section 3 : "Gestion complète",
# "Consultation + alertes", "Vue globale et statistiques").
GLOBAL_VIEW_ROLES = {ROLE_ADMIN, ROLE_CHEF_DE_PROJET, ROLE_DIRECTION_TECHNIQUE}
# Le Développeur, lui, est restreint aux projets associés à son rôle
# (section 3 : "Consultation des projets assignés").


def get_current_user(request):
    """Retourne le core.models.User choisi, ou None si personne n'est choisi."""
    user_id = request.session.get(SESSION_KEY)
    if not user_id:
        return None
    return User.objects.select_related("role").filter(id=user_id).first()


class IsAuthenticatedUMLMUser(BasePermission):
    """Refuse l'accès à l'API si personne n'est sélectionné via la session maison."""

    def has_permission(self, request, view):
        return get_current_user(request) is not None


def role_required(*allowed_roles):
    """
    Usage : @role_required("admin")
    Bloque l'accès aux pages de gestion si l'utilisateur sélectionné n'a pas
    un des rôles listés (utilisé par core/views_manage.py).
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = get_current_user(request)
            if not user:
                return redirect("/")
            role_name = getattr(user.role, "name", "").lower()
            if role_name not in allowed_roles:
                return redirect("/")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
