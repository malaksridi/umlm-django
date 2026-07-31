"""
Commande : python manage.py scan_modules

Pour chaque couple (Project, Module), compare le commit local au commit
GitHub, met à jour le status, l'historise, et déclenche des alertes
(section 4.5 du cahier des charges) — y compris un vrai envoi d'email
au staff pour les alertes critiques, et une notification interne stockée
pour toutes les alertes.

C'est cette commande qui remplace la mise à jour manuelle de l'Excel.
À lancer quotidiennement (via un cron / scheduled task Windows).
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.github_service import get_latest_commit, get_local_commit
from core.models import ProjectModule, Alert, User


# Libellés et couleurs par type d'alerte — utilisés dans l'email HTML
ALERT_LABELS = {
    "module_critique_retard": ("Module critique en retard", "#e11d48"),
    "module_absent": ("Module absent", "#d97706"),
    "diverged": ("États divergents", "#e11d48"),
    "retard_seuil_depasse": ("Retard prolongé", "#d97706"),
}
DEFAULT_ALERT_COLOR = "#4f46e5"


class Command(BaseCommand):
    help = "Scanne tous les couples projet/module, met à jour leur statut, et déclenche les alertes (email + notification interne)"

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
        Applique les règles de la section 4.5, crée les Alert nécessaires
        (une par canal : email + notification interne), et envoie un vrai
        email au staff pour chacune.
        """
        derniere_maj = pm.mises_a_jour.order_by("-scanned_at").first()
        if derniere_maj is None:
            return 0

        alerts_to_create = []

        if pm.status == ProjectModule.Status.BEHIND:
            if pm.module.criticality == "critique":
                alerts_to_create.append("module_critique_retard")

            # Seuil configurable, indépendant de la criticité (section 4.5 :
            # "le retard dépasse un seuil configurable")
            first_behind = (
                pm.mises_a_jour.filter(status=ProjectModule.Status.BEHIND)
                .order_by("scanned_at")
                .first()
            )
            if first_behind:
                delay_days = (timezone.now() - first_behind.scanned_at).days
                threshold = getattr(settings, "ALERT_DELAY_THRESHOLD_DAYS", 7)
                if delay_days >= threshold and "module_critique_retard" not in alerts_to_create:
                    alerts_to_create.append("retard_seuil_depasse")

        if pm.status == ProjectModule.Status.NON_INTEGRE:
            alerts_to_create.append("module_absent")

        if pm.status == ProjectModule.Status.DIVERGED:
            alerts_to_create.append("diverged")

        for alert_type in alerts_to_create:
            # Une alerte "email" (envoi réel) + une alerte "notification
            # interne" (stockée, affichée dans le dashboard) — section 4.5 :
            # "Canaux : Email, Notification interne"
            email_alert = Alert.objects.create(
                mise_a_jour=derniere_maj,
                type=alert_type,
                channel=Alert.Channel.EMAIL,
            )
            self.send_alert_email(pm, email_alert)

            Alert.objects.create(
                mise_a_jour=derniere_maj,
                type=alert_type,
                channel=Alert.Channel.NOTIFICATION_INTERNE,
            )

            self.stdout.write(self.style.WARNING(f"    -> Alerte créée (email + notification interne) : {alert_type}"))

        return len(alerts_to_create)

    def send_alert_email(self, pm: ProjectModule, alert: Alert):
        staff_emails = list(User.objects.exclude(email="").values_list("email", flat=True))
        if not staff_emails:
            self.stdout.write(self.style.WARNING("    (aucun utilisateur avec un email — alerte non envoyée)"))
            return

        label, color = ALERT_LABELS.get(alert.type, (alert.type, DEFAULT_ALERT_COLOR))
        subject = f"[UMLM] {label} — {pm.project.name} / {pm.module.name}"

        text_body = (
            f"Une alerte a été détectée par UMLM.\n\n"
            f"Type : {label}\n"
            f"Projet : {pm.project.name}\n"
            f"Module : {pm.module.name} (criticité : {pm.module.criticality})\n"
            f"Statut actuel : {pm.status}\n\n"
            f"Consultez le dashboard pour plus de détails : "
            f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/dashboard/"
        )
        html_body = self._build_html_email(pm, alert, label, color)

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,        # fallback texte brut pour les clients qui ne lisent pas le HTML
                from_email=None,       # utilise DEFAULT_FROM_EMAIL
                to=staff_emails,
            )
            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=False)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Échec de l'envoi d'email : {e}"))

    @staticmethod
    def _build_html_email(pm: ProjectModule, alert: Alert, label: str, color: str) -> str:
        dashboard_url = getattr(settings, "SITE_URL", "http://localhost:8000") + "/dashboard/"

        return f"""\
<!DOCTYPE html>
<html lang="fr">
<body style="margin:0; padding:0; background:#f0f2fd; font-family: Arial, Helvetica, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2fd; padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 16px rgba(0,0,0,0.06);">

          <!-- Header -->
          <tr>
            <td style="background:#4f46e5; padding:24px 28px;">
              <span style="font-family: Arial, Helvetica, sans-serif; font-size:12px; letter-spacing:2px; text-transform:uppercase; color:#e0e7ff; font-weight:bold;">
                UMLM — GESTION
              </span>
              <div style="font-family: Arial, Helvetica, sans-serif; font-size:20px; font-weight:bold; color:#ffffff; margin-top:6px;">
                Alerte système
              </div>
            </td>
          </tr>

          <!-- Alert type banner -->
          <tr>
            <td style="padding:0;">
              <div style="background:{color}1A; border-left:4px solid {color}; padding:14px 28px;">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{color}; margin-right:8px;"></span>
                <span style="font-family: Arial, Helvetica, sans-serif; font-size:14px; font-weight:bold; color:{color};">
                  {label}
                </span>
              </div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, Helvetica, sans-serif; font-size:14px; color:#1e1b4b;">
                <tr>
                  <td style="padding:8px 0; color:#64748b; width:120px;">Projet</td>
                  <td style="padding:8px 0; font-weight:bold;">{pm.project.name}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0; color:#64748b;">Module</td>
                  <td style="padding:8px 0; font-weight:bold;">{pm.module.name}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0; color:#64748b;">Criticité</td>
                  <td style="padding:8px 0;">
                    <span style="display:inline-block; background:#fef3c7; color:#d97706; font-size:12px; font-weight:bold; padding:3px 10px; border-radius:6px; text-transform:uppercase;">
                      {pm.module.criticality}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0; color:#64748b;">Statut actuel</td>
                  <td style="padding:8px 0; font-weight:bold;">{pm.status}</td>
                </tr>
              </table>

              <div style="margin-top:26px; text-align:center;">
                <a href="{dashboard_url}" style="display:inline-block; background:#4f46e5; color:#ffffff; text-decoration:none; font-family: Arial, Helvetica, sans-serif; font-size:13px; font-weight:bold; letter-spacing:0.3px; padding:12px 28px; border-radius:10px;">
                  Voir le dashboard
                </a>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:18px 28px; background:#f8f9fe; border-top:1px solid #e0e7ff;">
              <span style="font-family: Arial, Helvetica, sans-serif; font-size:11px; color:#94a3b8;">
                Cet email a été envoyé automatiquement par UMLM — UPS Module Lifecycle Manager.
                Ne pas répondre à cet email.
              </span>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
