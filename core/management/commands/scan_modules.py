"""
Commande : python manage.py scan_modules

Pour chaque couple (Project, Module), compare le commit local au commit
GitHub, met à jour le status, l'historise, et déclenche des alertes
(section 4.5 du cahier des charges) — y compris un vrai envoi d'email
au staff pour les alertes critiques.

C'est cette commande qui remplace la mise à jour manuelle de l'Excel.
À lancer quotidiennement (via un cron / scheduled task Windows).
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from core.github_service import get_latest_commit, get_local_commit
from core.models import ProjectModule, Alert, User


class Command(BaseCommand):
    help = "Scanne tous les couples projet/module, met à jour leur statut, et déclenche les alertes (email inclus)"

    def handle(self, *args, **options):
        project_modules = ProjectModule.objects.select_related("project", "module").all()
        nb_alerts = 0

        for pm in project_modules:
            github_commit = get_latest_commit(pm.module.github_url, pm.module.reference_branch)
            local_commit = get_local_commit(pm.project.local_path, pm.project.reference_branch)

            pm.github_commit = github_commit
            pm.local_commit = local_commit
            pm.update_status()  # recalcule le status + crée une MiseAJour

            self.stdout.write(f"{pm.project.name} / {pm.module.name} -> {pm.status}")

            nb_alerts += self.check_and_create_alerts(pm)

        self.stdout.write(self.style.SUCCESS(
            f"{project_modules.count()} couples scannés, {nb_alerts} alerte(s) créée(s)."
        ))

    def check_and_create_alerts(self, pm: ProjectModule) -> int:
        """
        Applique les règles de la section 4.5, crée les Alert nécessaires,
        et envoie un vrai email au staff pour chacune.
        """
        derniere_maj = pm.mises_a_jour.order_by("-scanned_at").first()
        if derniere_maj is None:
            return 0

        alerts_to_create = []

        if pm.status == ProjectModule.Status.BEHIND and pm.module.criticality == "critique":
            alerts_to_create.append("module_critique_retard")

        if pm.status == ProjectModule.Status.NON_INTEGRE:
            alerts_to_create.append("module_absent")

        if pm.status == ProjectModule.Status.DIVERGED:
            alerts_to_create.append("diverged")

        for alert_type in alerts_to_create:
            alert = Alert.objects.create(
                mise_a_jour=derniere_maj,
                type=alert_type,
                channel=Alert.Channel.EMAIL,
            )
            self.send_alert_email(pm, alert)
            self.stdout.write(self.style.WARNING(f"    -> Alerte créée + email envoyé : {alert_type}"))

        return len(alerts_to_create)

    def send_alert_email(self, pm: ProjectModule, alert: Alert):
        staff_emails = list(User.objects.exclude(email="").values_list("email", flat=True))
        if not staff_emails:
            self.stdout.write(self.style.WARNING("    (aucun utilisateur avec un email — alerte non envoyée)"))
            return

        subject = f"[UMLM] Alerte : {alert.type} — {pm.project.name} / {pm.module.name}"
        message = (
            f"Une alerte a été détectée par UMLM.\n\n"
            f"Type : {alert.type}\n"
            f"Projet : {pm.project.name}\n"
            f"Module : {pm.module.name} (criticité : {pm.module.criticality})\n"
            f"Statut actuel : {pm.status}\n\n"
            f"Consultez le dashboard pour plus de détails."
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,  # utilise DEFAULT_FROM_EMAIL
                recipient_list=staff_emails,
                fail_silently=False,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Échec de l'envoi d'email : {e}"))
