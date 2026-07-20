"""
Commande : python manage.py scan_modules

Pour chaque couple (Project, Module), compare le commit local au commit
GitHub, met à jour le status, l'historise, et déclenche des alertes
si nécessaire (section 4.5 du cahier des charges).

C'est cette commande qui remplace la mise à jour manuelle de l'Excel.
À lancer quotidiennement (via un cron / scheduled task Windows).
"""
from django.core.management.base import BaseCommand

from core.github_service import get_latest_commit, get_local_commit
from core.models import ProjectModule, Alert


class Command(BaseCommand):
    help = "Scanne tous les couples projet/module, met à jour leur statut, et déclenche les alertes"

    def handle(self, *args, **options):
        project_modules = ProjectModule.objects.select_related("project", "module").all()
        nb_alerts = 0

        for pm in project_modules:
            github_commit = get_latest_commit(pm.module.github_url, pm.module.reference_branch)
            local_commit = get_local_commit(pm.project.local_path, pm.project.reference_branch)

            pm.github_commit = github_commit
            pm.local_commit = local_commit
            pm.update_status()  # recalcule le status + crée une MiseAJour (dernière créée = ci-dessous)

            self.stdout.write(f"{pm.project.name} / {pm.module.name} -> {pm.status}")

            nb_alerts += self.check_and_create_alerts(pm)

        self.stdout.write(self.style.SUCCESS(
            f"{project_modules.count()} couples scannés, {nb_alerts} alerte(s) créée(s)."
        ))

    def check_and_create_alerts(self, pm: ProjectModule) -> int:
        """
        Applique les règles de la section 4.5 et crée les Alert nécessaires.
        Retourne le nombre d'alertes créées pour ce couple.
        """
        # La MiseAJour vient d'être créée dans update_status() -> on prend la plus récente
        derniere_maj = pm.mises_a_jour.order_by("-scanned_at").first()
        if derniere_maj is None:
            return 0

        alerts_to_create = []

        # Règle 1 : module critique en retard
        if pm.status == ProjectModule.Status.BEHIND and pm.module.criticality == "critique":
            alerts_to_create.append("module_critique_retard")

        # Règle 2 : module attendu absent
        if pm.status == ProjectModule.Status.NON_INTEGRE:
            alerts_to_create.append("module_absent")

        # Règle 3 : état Diverged détecté
        if pm.status == ProjectModule.Status.DIVERGED:
            alerts_to_create.append("diverged")

        for alert_type in alerts_to_create:
            Alert.objects.create(
                mise_a_jour=derniere_maj,
                type=alert_type,
                channel=Alert.Channel.NOTIFICATION_INTERNE,
            )
            self.stdout.write(self.style.WARNING(f"    -> Alerte créée : {alert_type}"))

        return len(alerts_to_create)
