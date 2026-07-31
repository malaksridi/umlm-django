# Destination: core/forms_manage.py  (replace the whole file)
from django import forms
from .models import Project, Module, Role, User


class ProjectForm(forms.ModelForm):
    # Non-model field: which modules are "expected" on this project
    # (cahier des charges 4.1 : "Associer les modules attendus")
    modules = forms.ModelMultipleChoiceField(
        queryset=Module.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Modules attendus",
    )

    class Meta:
        model = Project
        # "roles" is a real ManyToMany field on Project — determines which
        # Développeurs see this project (section 3 : "projets assignés")
        fields = ["name", "local_path", "reference_branch", "roles"]
        widgets = {
            "roles": forms.CheckboxSelectMultiple,
        }
        labels = {
            "roles": "Rôles assignés",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Pre-check the modules already associated with this project
            self.fields["modules"].initial = Module.objects.filter(
                project_modules__project=self.instance
            )


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["name", "github_url", "reference_branch", "criticality", "is_custom_fork"]


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = [
            "name",
            "droit_gestion_complete",
            "droit_consultation",
            "droit_alertes",
            "droit_consultation_projets_assignes",
            "droit_vue_globale_statistiques",
        ]
        labels = {
            "droit_gestion_complete": "Gestion complète",
            "droit_consultation": "Consultation",
            "droit_alertes": "Alertes",
            "droit_consultation_projets_assignes": "Consultation des projets assignés",
            "droit_vue_globale_statistiques": "Vue globale et statistiques",
        }


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "role"]
