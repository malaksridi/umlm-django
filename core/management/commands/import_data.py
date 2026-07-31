"""
Commande : python manage.py import_data

Lit data/projects.json et data/modules.json, et peuple la base de données.
Remplace la logique "on ajoute un projet à la main dans un formulaire" :
on modifie juste les fichiers JSON, puis on relance cette commande.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Project, Module, ProjectModule

DATA_DIR = Path(settings.BASE_DIR) / "data"


class Command(BaseCommand):
    help = "Importe projects.json et modules.json dans la base de données"

    def handle(self, *args, **options):
        self.import_projects()
        self.import_modules()
        self.stdout.write(self.style.SUCCESS("Import terminé."))

    def import_projects(self):
        with open(DATA_DIR / "projects.json", encoding="utf-8") as f:
            projects = json.load(f)

        for p in projects:
            obj, created = Project.objects.update_or_create(
                name=p["name"],
                defaults={
                    "github_url": p["github_url"],
                    "reference_branch": p.get("reference_branch", "main"),
                },
            )
            action = "créé" if created else "mis à jour"
            self.stdout.write(f"  Projet {obj.name} : {action}")

    def import_modules(self):
        with open(DATA_DIR / "modules.json", encoding="utf-8") as f:
            modules = json.load(f)

        for m in modules:
            module_obj, created = Module.objects.update_or_create(
                name=m["name"],
                defaults={
                    "github_url": m["github_url"],
                    "reference_branch": m.get("reference_branch", "main"),
                    "criticality": m.get("criticality", "moyen"),
                    "is_custom_fork": m.get("is_custom_fork", False),
                },
            )
            action = "créé" if created else "mis à jour"
            self.stdout.write(f"  Module {module_obj.name} : {action}")

            # Crée la classe-association ProjectModule pour chaque projet listé
            for project_name in m.get("used_in", []):
                try:
                    project_obj = Project.objects.get(name=project_name)
                except Project.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"    Projet '{project_name}' introuvable pour le module {module_obj.name} — ignoré"
                    ))
                    continue

                ProjectModule.objects.get_or_create(project=project_obj, module=module_obj)
                self.stdout.write(f"    Lié à {project_name}")
