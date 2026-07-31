from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=50)  # admin, chef_de_projet, developpeur, direction_technique
    created_at = models.DateTimeField(auto_now_add=True)

    # Droits — un checkbox par droit distinct du cahier des charges (section 3)
    droit_gestion_complete = models.BooleanField(default=False)              # Administrateur
    droit_consultation = models.BooleanField(default=False)                  # Chef de projet
    droit_alertes = models.BooleanField(default=False)                       # Chef de projet
    droit_consultation_projets_assignes = models.BooleanField(default=False) # Développeur
    droit_vue_globale_statistiques = models.BooleanField(default=False)      # Direction technique

    @property
    def nombre_utilisateurs(self):
        return self.users.count()

    def __str__(self):
        return self.name


class User(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users")

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=255, unique=True)
    github_url = models.URLField(max_length=500)
    reference_branch = models.CharField(max_length=100, default="main")
    # Rôles assignés à ce projet — détermine quels Développeurs le voient
    # (cahier des charges section 3 : "Consultation des projets assignés")
    roles = models.ManyToManyField(Role, related_name="projects", blank=True)

    def __str__(self):
        return self.name


class Module(models.Model):
    class Criticality(models.TextChoices):
        FAIBLE = "faible"
        MOYEN = "moyen"
        CRITIQUE = "critique"

    name = models.CharField(max_length=255)
    github_url = models.URLField()
    reference_branch = models.CharField(max_length=100, default="main")
    criticality = models.CharField(max_length=10, choices=Criticality.choices, default=Criticality.MOYEN)
    is_custom_fork = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ProjectModule(models.Model):
    """
    Classe-association Project <-> Module : capture l'état d'UN module
    dans UN projet précis (cf. diagramme de classes validé).
    """
    class Status(models.TextChoices):
        NON_INTEGRE = "non_integre"
        UP_TO_DATE = "up_to_date"
        BEHIND = "behind"
        AHEAD = "ahead"
        DIVERGED = "diverged"
        FORK_PERSONNALISE = "fork_personnalise"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_modules")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="project_modules")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NON_INTEGRE)
    local_commit = models.CharField(max_length=100, blank=True, null=True)
    github_commit = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ("project", "module")

    def __str__(self):
        return f"{self.project.name} / {self.module.name} ({self.status})"

    def update_status(self):
        """
        Recalcule le status à partir de local_commit / github_commit.
        Appelé après un scan GitHub (voir github_service.py).

        Utilise l'API "compare" de GitHub (github_service.compare_commits)
        pour distinguer correctement BEHIND / AHEAD / DIVERGED plutôt que
        de tout classer en BEHIND. Si la comparaison échoue (ex: le
        commit local n'a jamais été poussé sur GitHub), on retombe sur
        BEHIND par défaut — le cas le plus courant en pratique.
        """
        # Un fork personnalisé ignore volontairement les mises à jour
        # (cahier des charges section 4.3 : "Mises à jour ignorées volontairement")
        if self.module.is_custom_fork:
            self.status = self.Status.FORK_PERSONNALISE
        elif not self.local_commit:
            self.status = self.Status.NON_INTEGRE
        elif self.local_commit == self.github_commit:
            self.status = self.Status.UP_TO_DATE
        else:
            from core.github_service import compare_commits
            comparison = compare_commits(
                self.module.github_url, base=self.local_commit, head=self.github_commit
            )
            if comparison == "ahead":
                self.status = self.Status.BEHIND
            elif comparison == "behind":
                self.status = self.Status.AHEAD
            elif comparison == "diverged":
                self.status = self.Status.DIVERGED
            elif comparison == "identical":
                self.status = self.Status.UP_TO_DATE
            else:
                self.status = self.Status.BEHIND
        self.save()

        # Historise ce résultat (section 4.6)
        MiseAJour.objects.create(project_module=self, status=self.status)


class MiseAJour(models.Model):
    """Historique : un enregistrement par scan (section 4.6)."""
    project_module = models.ForeignKey(ProjectModule, on_delete=models.CASCADE, related_name="mises_a_jour")
    status = models.CharField(max_length=20)
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project_module} @ {self.scanned_at}"


class Alert(models.Model):
    """Déclenchée par une mise à jour (section 4.5)."""
    class Channel(models.TextChoices):
        EMAIL = "email"
        NOTIFICATION_INTERNE = "notification_interne"
        TEAMS_SLACK = "teams_slack"

    mise_a_jour = models.ForeignKey(MiseAJour, on_delete=models.CASCADE, related_name="alerts")
    type = models.CharField(max_length=100)  # ex: module_critique_retard, module_absent, diverged, retard_seuil_depasse
    channel = models.CharField(max_length=25, choices=Channel.choices, default=Channel.NOTIFICATION_INTERNE)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} ({self.channel})"
